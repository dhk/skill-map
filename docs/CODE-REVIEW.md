# Code Review — crawlers/ (skill-map)

Reviewer pass focused on three things you asked for: **(1) assumptions & fragile
dependencies, (2) where deterministic code can replace LLM instructions, and
(3) data we could gather/store *once* during the crawl to avoid re-fetching it
later.** Detailed notes live inline as `# REVIEW(...)` comments; this file is the
map. Grep the tree with `grep -rn "REVIEW(" crawlers/` to walk them in order.

The pipeline is genuinely well-built — idempotent stages, immutable snapshots, a
single `gen_stats`/`check_docs` source of truth, resilient mid-crawl writes. The
findings below are about the seams between stages, not the core design.

## How many skills do we *really* have?

`crawlers/count_skills.py` answers this with a dedup funnel (writes
`data/unique_counts.json`):

| stage | count |
|---|---|
| raw crawl records | 5,393 |
| Claude SKILL.md with content | 4,975 |
| Gemini files (metadata only, catalogued not built) | 418 |
| distinct `(repo, file_path)` | 4,975 |
| distinct **exact** bodies | 3,846 |
| **distinct skills (exact + ≥0.80 near-dup collapsed)** | **3,769** |
| distinct concepts (same idea, any wording) | 2,681 |

So the honest headline is **~3,769 unique skills**, not 4,902/4,975 — about **24%
of fetched files are exact or near-duplicate copies** of another skill (the
mega-collections re-publishing each other). It reuses the same clustering method
as `lineage_trace.py`, so the number is consistent with the copy/lineage analysis.
This is a candidate to fold into `gen_stats`/STATS.md as the canonical figure.

---

## 1. Fragile dependencies & hidden assumptions

### High impact

- **Stale single-crawl pin.** ✅ *Fixed on this branch.* `judge_llm.py`,
  `sample_llm.py`, and `lineage_trace.py` hard-coded
  `crawls/crawl-1-2026-06-24/data.json` while `score_corpus`/`track_history` read
  the **merged** corpus, so after any re-crawl the judge/lineage read
  first-snapshot content but compared against current scores. They now route
  through the canonical `load_all_crawls()` / new `latest_content_by_key()`
  (4,975 skills with content vs crawl-1's subset). This also removes a latent
  `KeyError`: the judges sample from the full corpus but used to look up content
  in crawl-1 only. (`maturity_crawl.py` is retired; left pinned with a note.)

- **`load_all_crawls()` "latest wins" sorted lexically.** ✅ *Fixed on this
  branch.* It picked the most-recent crawl by `sorted()` on the dir name, so once
  there are ≥10 crawls `crawl-10-…` sorts *before* `crawl-2-…` and an older
  snapshot silently wins the merge. Now sorts by the numeric `<n>` via `_crawl_n`.

- **`index.html` is used as a database.** `tag_skills`, `reclassify`,
  `enrich_urls`, `patch_map_badges` each re-implement `const GRAPH = ({.*?});\n`
  with **inconsistent** `re.S` flags. The no-DOTALL variants only work because the
  GRAPH blob stays minified on one line; pretty-print it once and half the
  toolchain stops matching. *Fix: one shared `load_graph`/`save_graph`, or store
  the graph as a real `.json` the page fetches.*

- **Branch assumptions.** The crawl writes raw URLs as `/HEAD/`; `enrich_urls`
  writes source links as `/tree/main/` (404s on master/develop repos);
  `patch_map_badges` reads them back with `/tree/[^/]+/`. Three files, three
  different ideas of the branch. `get_repo_meta` should just capture
  `default_branch`.

### Medium impact

- **Tree-API truncation never checked** (`crawl.py`, `fetch_siblings.py`). The
  recursive trees API truncates at ~100k entries and sets `truncated=True`; we
  ignore it, so SKILL.md/sibling files past the cutoff vanish silently on large
  monorepos.
- **Global-search mode isn't incremental.** Global results carry no blob SHA, and
  the SHA-diff skip requires a truthy SHA — so global crawls re-fetch the whole
  corpus every time. (Repo-scoped mode is fine.)
- **Two definitions of "a skill."** `walk_repo_tree` matches only `SKILL.md`
  (case-insensitive); `GLOBAL_QUERIES` also matches `skill.md`/`SKILLS.md`. The
  two crawl paths disagree on membership.
- **Unauthenticated GitHub API at scale.** `fetch_siblings`, `lineage_trace`, and
  `judge_llm.fetch_siblings` hit the API unauth (60 req/hr) with bare `except`
  that turns rate-limit exhaustion into silently-dropped data. `maturity_crawl`
  already threads `$GITHUB_TOKEN` — copy that.
- **`git_commit_push` runs bare `git push`** (no remote/branch) and commits only
  `crawls/<id>/`, leaving the regenerated `data/`+`docs/` uncommitted — a crawl
  can ship with stale published stats.
- **One-crawl-per-day resumption** (`find_today_dir`): two different lists on the
  same day merge into one dir and the quality metrics reflect only the last list.
- **Scoring inconsistency.** `track_history` scores without `sibling_files` while
  `score_corpus` scores with it, so a skill's "quality" differs between
  `skill_history.json` and `STATS.md`, and history "movers" can be the siblings
  sidecar appearing, not the skill changing.
- **Hand-rolled YAML** (`skill_quality.parse_skill`): flat keys + block scalars
  only; nested `metadata:`, flow lists, and colon-bearing values mis-parse and
  mis-score frontmatter. Use a real YAML lib with a fallback.
- **Frozen thresholds.** Every constant in `skill_quality.py` is pinned from one
  anthropics/skills snapshot and never recomputed; `check_docs` likewise hunts
  hard-coded stale numbers it can't auto-discover.

---

## 2. Deterministic code that can replace LLM instructions

- **`tag_skills.py` — the strongest case.** One `claude -p` call *per skill*
  (~1,121) for a **closed-vocabulary** classification, and it already falls back
  to a deterministic default on bad output. Three of the four axes are nearly
  free deterministically:
  - `action` already exists twice — in `gen_types.py`'s regex map and
    `skill_quality.WHAT_PATTERNS`.
  - `output_type` reads off the body (fenced code → code; JSON/YAML/table →
    structured-data; "report" → report; media verbs → media).
  - `integration` keys on signals the crawl has (allowed-tools/mcp/api/sdk →
    connector; orchestrat/pipeline/agent → orchestrator).
  - `complexity` is the only fuzzy axis, and proxies well from body length +
    numbered steps + ref-file count.
  A deterministic tagger would be reproducible, free, and pipeline-able (this
  script is currently manual). Keep an *optional* LLM pass for residual ambiguity.

- **LLM judges, scoped down.** `sample_llm`/`judge_llm` grade eight axes; four
  (frontmatter, triggering, disclosure, structure) are **already** computed
  deterministically over the whole corpus by `skill_quality.py`. The LLM is only
  genuinely additive on the three judgment axes it flags itself — scope,
  instruction quality, safety appropriateness. Scope the LLM to those.

- **`reclassify.py` domain assignment** is a ~100-entry hand-maintained
  skill→domain dict plus hard-coded per-domain counts. This is the *opposite*
  case: domain assignment is open-vocabulary and semantic, so it's where an LLM
  classifier would be **defensible** — but today it's neither LLM nor data-driven,
  just a manual map that rots every crawl. Either a deterministic
  topic/keyword classifier (using the already-gathered `repo_topics`) or a real
  LLM pass; the hand-edited dict is the wrong tool, and the counts must be derived.

*(`v1` `sample_llm.py` is superseded by `judge_llm.py` per its own docstring,
still carries the 6000-char truncation bug it was written to fix, and isn't
retired — retire it like `maturity_crawl.py`.)*

---

## 3. Expand what each crawl gathers — to avoid rework

The crawl is the only authenticated, rate-limit-aware pass. Everything downstream
re-derives data over the unauth API. Capturing more *during* `walk_repo_tree` /
`get_repo_meta` deletes whole network stages:

| Capture during crawl | Eliminates / fixes | Today's cost |
|---|---|---|
| **Full per-repo blob list / per-skill siblings** (the tree walk already has it) | all of `fetch_siblings.py`; `judge_llm.fetch_siblings`; real data for the disclosure axis | a second + third unauth tree fetch, rate-limited |
| **`default_branch`** (one extra field on the `get_repo` we already make) | branch re-fetches in `fetch_siblings`/`audit_repo`; the hard-coded `main` in `enrich_urls` | broken source links + redundant calls |
| **Blob SHA on global-search results** | makes global crawls incremental | full re-fetch every global crawl |
| **First/last commit date per file** (if affordable) | the per-file commits-API passes in `lineage_trace` + `maturity_crawl` | 1–2 unauth calls *per file*, guaranteed rate-limit |
| **`repo_topics` wired into domain classification** (already gathered, unused) | most of `reclassify.py`'s manual MOVES dict | ~100 hand-maintained mappings |

Net: storing siblings + default_branch + global SHAs at crawl time removes two
unauthenticated network passes, fixes the disclosure-axis blindspot at its source,
and makes both crawl modes incremental — for a handful of extra fields on data we
already hold in memory.

---

## Prototypes implemented on this branch

The highest-leverage fixes above are now implemented (the rest remain as inline
`REVIEW(...)` notes):

**A. Siblings + `default_branch` captured during the crawl** (`crawl.py`,
`fetch_siblings.py`). `walk_repo_tree` now stores each skill's `sibling_files`
(same contract as `data/sibling_files.json`, cap 60) straight from the tree it
already walks, checks the truncation flag, and `get_repo_meta` captures
`repo_default_branch`. `fetch_siblings.py` gained a fast path that harvests those
from the crawl snapshots and only hits the unauthenticated API for repos crawled
*before* this change. Verified: all 4,975 existing skills route to the legacy
backfill (no silent-empty regression); every future crawl populates siblings with
zero extra network calls, deleting that whole pass. The sibling helper output is
byte-for-byte identical to the old API-derived format.

**B. Deterministic tagger** (`classify_tags.py`) — a drop-in for `tag_skills.py`'s
per-skill `claude -p` classifier. Same 4 dimensions, same cache/patch shape,
classifies from the same inputs the LLM saw. `--compare` scores it against the
157 real LLM tags:

| axis | deterministic | majority-class baseline |
|---|---|---|
| action | **53%** | 22% |
| complexity | **66%** | 60% |
| output_type | **48%** | 27% |
| integration | **57%** | 38% |

Every axis beats its baseline by 1.5–2.4×, from label+description+domain alone and
at zero marginal cost. `output_type` is weakest because the LLM's own calls there
are inconsistent (docx→"media" but pptx→"generate" on near-identical text).
Classifying from the full corpus (body + frontmatter + the now-captured siblings)
rather than the truncated graph node would lift every axis further — the
recommendation stands: deterministic default, optional LLM only for the
ambiguous tail.

**C. Canonical merged-corpus loader** (`score_corpus.py` + the three consumers).
`load_all_crawls()` now sorts by numeric crawl index (`_crawl_n`) so `crawl-10`
can't lose to `crawl-2`, and a new `latest_content_by_key()` wrapper is the one
"latest content per skill" definition. `judge_llm.py`, `sample_llm.py`, and
`lineage_trace.py` were switched off their hard-coded crawl-1 pin onto it — so
re-crawls flow through the LLM judges and the lineage/originator/curiosities
chain, and the judges' content lookups can no longer `KeyError` on
later-crawl skills. Verified against live data (5,393 merged records, 4,975 with
content).

**D. Remaining seams closed.**
- **`graphio.py`** — one `load_graph`/`save_graph`/`skill_nodes` helper; the four
  scripts that hand-rolled the `const GRAPH = …` regex (tag_skills, reclassify,
  enrich_urls, patch_map_badges) + classify_tags now share it. No more
  inconsistent-`re.S` time bomb.
- **`skill_quality.parse_skill`** uses PyYAML (with the hand parser as fallback
  for absent/malformed YAML). Regression-checked: 99% of scores identical, mean
  |Δ|0.18; the 54 movers are genuine fixes (e.g. multi-line plain-scalar
  descriptions the old parser read as empty).
- **`reclassify.py`** — counts are derived from membership (the hard-coded ones
  were wildly off: `Platform & APIs` said 195, actual 25); a keyword
  `classify_domain()` auto-places anything not in the explicit MOVES override; I/O
  via graphio.
- **`track_history.py`** scores WITH siblings (matches STATS) and iterates crawls
  in numeric order (`_crawl_n`).
- **`enrich_urls.py`** matches on `(org, dir)` not bare basename, uses the
  crawl-captured `default_branch` (HEAD fallback) instead of hard-coded `main`,
  reads the merged corpus.
- **`crawl.py`** — shared `is_skill_file()` so repo-scoped and global-search agree
  on membership; global-search now captures blob SHAs (incremental); hardened
  `git push -u origin <branch>` with detached-HEAD guard.
- **`check_docs.py`** — generic headline-drift check (flags any "N skills across…
  / N repos" ≠ live) on top of the curated list; caught stale 4,953/41 the old
  list missed.
- **`curiosities.py`** — dead `most_code` placeholder removed.

## What's solid (don't change)

`score_corpus` / `skill_quality` / `repo_signature` are clean, fast, fully
deterministic, and reusable (`audit_repo` rides them for the private-repo
deliverable). `gen_stats` + `check_docs` as a single source of truth is the right
instinct — the recommendation above is mostly to extend that same "derive, don't
hand-write" discipline to domains, tags, and the index.html graph.
