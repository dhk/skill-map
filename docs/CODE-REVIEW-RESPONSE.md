# Code Review Response & Action List (review2)

Second-pass triage of PR #5 (`docs/CODE-REVIEW.md` + the fixes on
`claude/skill-map-code-review-hx98b1`). Two reviewers converged here; this is the
merged result.

**Verdict: sound, mergeable.** Verified against live runs — pipeline green, score
parity held (median 82.5, WHEN +1pt from the better YAML parser), all modules
parse, and a re-run produced byte-identical derived JSON (only the Sankey PNG
differs, due to matplotlib timestamp metadata). No correctness changes are
*required* to merge.

Inline counterparts carry the same tag: `grep -rn 'RECOMMEND(review2' .`
Priorities: **P0** = before merge · **P1** = should · **backlog** = optional.

---

## P0 — merge blocker (1) — ✅ DONE

- [x] **`docs/internal-skill-map.md:264` — stale `1,119 skills`.** The branch's
  own generic `check_docs` flagged it, so the PR failed its own doc gate. Fixed:
  the cell now reads `4,975 crawled skills (~3,769 unique)` — matches the live
  corpus and carries the honest dedup number. `check_docs` no longer flags it.

> The 2 remaining `check_docs` hits are intentional prose — an **article-draft
> hook** (`article-series.md`) and an **approximate** `~4,900` in
> `design-brief.md`. Author's call, not blockers.

---

## P1 — recommended polish — ✅ DONE

- [x] **`patch_map_badges.py` badge drop — FULLY RESOLVED.** Symptom: unmatched
  nodes now have their badge **cleared** (no stale grade) and the script logs
  `matched/cleared`. Root cause: fixed in `enrich_urls.py` (see backlog #3) — it
  now deep-links to each skill's *actual crawled location* (canonical > most-
  starred) when the `(org,dir)` attribution isn't in the corpus. Live map: 44
  deep-links (28 exact + 16 located), **41 badges, 0 stale**.
- [x] **Honest tagger framing.** `docs/CODE-REVIEW.md` §B and the
  `RECOMMEND(review2)` marker in `classify_tags.py` now state plainly: all-4-axes
  agreement ~12% — a default/gap-filler (`--fill` never overwrites LLM tags), not
  a replacement.

---

## Backlog — ✅ ALL DONE (one commit each)

1. [x] **`$GITHUB_TOKEN` threaded** into all unauth API calls via new
   `crawlers/ghapi.py` (lineage_trace, fetch_siblings, judge_llm — which now also
   prefers the sibling sidecar). 5,000 req/hr vs 60; raises instead of silently
   dropping data.
2. [x] **Tree-API `truncated` handled** — `crawl.py._all_blobs_bfs` and
   `fetch_siblings._blobs_bfs` walk per-directory (no flat 100k cap) when the
   recursive tree is truncated.
3. [x] **`enrich_urls` deep-link coverage** — falls back from `(org,dir)` to the
   skill's actual crawled location (canonical > stars); restored 16 deep-links /
   the badge join (see P1 above).
4. [x] **Per-list crawl dir** — `crawl-<n>-<date>-<slug>`; `find_today_dir(date,
   slug)` exact-suffix match, so same-day lists no longer merge.
5. [x] **`default_branch` finished** — `enrich_urls.resolve_branches()` (cached
   `data/repo_branches.json`, token-resolved) replaces `/tree/HEAD/` with the real
   branch for all 44 deep-links; HEAD is the offline fallback.
6. [x] **Thresholds derivable** — `skill_quality.calibrate()` re-derives the soft
   cutoffs from the canonical set (`score_corpus --calibrate`); constants are the
   fallback. Opt-in so committed scores don't shift.
7. [x] **`reclassify` topic-aware** — `ORG_TOPICS` joins crawl `repo_topics` by
   org into `classify_domain`.

---

## ✅ Already done — DO NOT re-flag

Landed on this branch; verified present:

- Unique-skill count folded into `STATS.md` (`gen_stats.py`) → "~3,769 unique skills".
- Stale single-crawl pin removed → judges/lineage read the merged corpus
  (`load_all_crawls()` / `latest_content_by_key()`); numeric `_crawl_n` sort.
- Hand-rolled YAML → PyYAML with fallback (99% scores identical; 54 movers are fixes).
- 4 inconsistent `const GRAPH` regexes → single `graphio.py` helper (5 scripts).
- `enrich_urls` `(org,dir)` match; `track_history` scores with siblings + numeric
  order; `git push -u origin <branch>`; `crawl.py` shared `is_skill_file()` +
  global-search blob SHAs.
- `lineage_trace` `Counter` `UnboundLocalError` (no-dates path) fixed.
- `sample_llm.py` retired; `reclassify` + `classify_tags --fill` wired into `run_pipeline`.
- Dead code (`curiosities.most_code`) removed.

## 🛑 Don't touch — load-bearing / correct-as-is

- `score_corpus` / `skill_quality` / `repo_signature` / `gen_stats` + `check_docs`
  are the clean "derive, don't hand-write" core.
- `graphio.GRAPH_RE` uses `re.S` and `save_graph` writes minified — keep both;
  the old no-DOTALL copies only worked by accident.
- `classify_tags --fill` preserves existing tags — do NOT switch the pipeline to
  `--patch` (that overwrites 157 LLM tags with ~12%-parity deterministic ones).
- `sibling_files = None` vs `[]` (`crawl.py`) — `None` = not walked (→ API
  backfill); `[]` = walked, genuinely empty. Don't collapse them.
- Reduced map deep-links/badges (28/26) is the *correct* result of dropping
  cross-repo mis-links — don't "restore" coverage by loosening the match (fix the
  root cause in `enrich_urls` instead).
- `count_skills` near-dup threshold 0.80 matches `lineage_trace` on purpose.
- `maturity_crawl.py` / `sample_llm.py` kept-but-retired — intentional (history).
- Committed derived data is consistent with a fresh pipeline run; no forced regen
  needed on merge (only the Sankey PNG differs, on matplotlib metadata).
