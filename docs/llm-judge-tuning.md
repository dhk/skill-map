# Tuning the LLM Judge — why it scored Anthropic "weak," and the fix

The first LLM cross-read (`crawlers/sample_llm.py`, data in `llm_sample.json`)
labelled even `anthropics/skills` and `openai/skills` as **"weak"**. That's a
judge problem, not a skill problem. This is the post-mortem and the fix
(`crawlers/judge_llm.py`).

## Why it scored the gold standard poorly

Three causes — two are harness bugs, one is prompt design.

### 1. Truncation artifact (harness bug)
`sample_llm.py` clipped every skill to **6,000 characters** before the judge saw
it. But:

| Skill | Real size | Fed to judge |
|---|---|---|
| `anthropics/skills/xlsx` | 11,455 chars | 6,000 (47% cut) |
| `openai/skills/figma-use` | 17,717 chars | 6,000 (66% cut) |
| `obra/superpowers/writing-plans` | 7,070 chars | 6,000 |

The judge then reported *"document is truncated mid-sentence… incomplete /
unshippable"* — penalising a cut **we** made. It hit the longest skills hardest,
which are disproportionately the well-developed ones.

### 2. No reference-file visibility (crawl + harness bug)
The judge's single most common complaint was *"no progressive disclosure — rules
dumped inline instead of linked to reference files."* But the crawl only fetched
`SKILL.md`. It never saw the sibling files. Checking the actual repos:

```
anthropics/skills/skills/xlsx/        → SKILL.md, scripts/ (recalc.py, office/)
anthropics/skills/skills/mcp-builder/ → SKILL.md, reference/, scripts/
anthropics/skills/skills/docx/        → SKILL.md, scripts/ (accept_changes.py, …)
anthropics/skills/skills/claude-api/  → SKILL.md, python/ go/ java/ ruby/ …
```

The skills **do** delegate depth to reference/scripts dirs. The judge marked them
down for an absence it simply couldn't see.

### 3. No calibration anchor (prompt design)
The v1 prompt offered `exemplary|solid|weak|broken` but never defined what
"exemplary" looks like, and asked for one holistic verdict against four high
bars. With no positive exemplar and no per-axis decomposition, the model
regresses to the pessimistic middle — everything becomes "weak."

The underlying signal was still sound: every **"broken"** verdict landed on a
genuine floor case (the `template` stubs, heuristic 43–45). The judge's *floor*
was calibrated; its *ceiling* was not.

## The fixes (`crawlers/judge_llm.py`)

1. **No truncation.** Pass the full file (cap at 32k chars, well above any real
   skill; if clipped, explicitly tell the model not to penalise length).
2. **Inject the sibling file listing.** Fetch the skill folder's contents (and
   one level into `reference/` / `scripts/`) and give it to the judge, with the
   instruction that progressive disclosure is satisfied when depth lives in those
   files. Inlining is only a defect when no such files exist.
3. **Per-axis 0–10 scoring with anchors** (frontmatter, triggering, disclosure,
   structure, tone, scope) plus a one-shot exemplar describing a 9–10 skill. This
   stops the all-or-nothing collapse and makes the LLM score comparable to the
   heuristic.

## Before / after (targeted re-judge)

| Skill | v1 verdict | v2 verdict | v2 axis mean | Genuine residual issue |
|---|---|---|---|---|
| `anthropics/xlsx` | weak | **solid** | 8.2 | conventions inlined; no `reference/` dir to skim |
| `openai/figma-use` | weak | **solid** | 7.0 | no anti-trigger note; alarmist tone (axis 5) |
| `openai/migrate-to-codex` | weak | **solid** | 6.8 | one-sentence description, no WHEN clause |
| `posit-dev/alt-text` | weak | **exemplary** | 8.5 | no anti-trigger clause |

Every skill recovered from "weak." The artifacts (truncation, invisible refs)
dissolved; what remains is **genuine, per-axis** feedback — and one consistent,
real finding the v1 noise had buried: **even canonical skills rarely state when
NOT to invoke** (an anti-trigger note). That's a legitimate, ecosystem-wide
improvement worth adding to the rubric.

## "Should we improve the Anthropic skills to score higher?"

Only **after** the judge is fixed — most of v1's criticism was measurement error.
Re-run with v2, and the *residual* critiques are the real, upstream-worthy ones:

- `xlsx`: disclosure axis still 5 — its description runs long (>200 words) and a
  fair amount of formatting guidance is genuinely inline rather than in a
  reference file. A legitimate (minor) improvement.
- `figma-use` (OpenAI): tone axis 7 — "MANDATORY", "NEVER", alarmist imperatives,
  plus duplicate list numbering. A legitimate style critique.

These are the kind of findings worth feeding back. The truncation and
"missing reference files" complaints are not — they were ours.

## Does maturity (age / commits) predict quality?

Separate question, answered from the crawl metadata we have (repo-level only):

| Signal | Correlation with repo median quality |
|---|---|
| log₁₀(stars) | 0.16 (negligible) |
| days-since-last-push | 0.10 (negligible) |

Star tiers don't move monotonically (>10k: 87, 1k–10k: 81, <1k: 88). **Popularity
and recency do not predict definition quality** — the repo *signature* dominates.

The one maturity proxy repo-level data can't test is **per-skill commit count**
(how much a skill has been iterated). The main crawl captured no git history, so
`crawlers/maturity_crawl.py` fetches it per file via the GitHub commits API
(`?path=<file>`) and correlates against the heuristic score.

The answer fails on **two independent grounds**.

**Ground 1 — commit count is uncorrelated with quality.** Across 172 skills from
9 repos spanning every signature:

| Metric | Value |
|---|---|
| corr(commit count, quality) | **−0.002** (zero) |

There is simply no relationship. More commits do not mean better definitions.

**Ground 2 — for the biggest repos, commit history isn't a maturity signal at
all, because skills are bulk-published.** People iterate a skill locally (or copy
it wholesale from elsewhere) and land it in the repo as a single snapshot commit.
The repo's git history then reflects *publishing*, not *development* — exactly as
suspected. The bulk-publish detector (`maturity_crawl.py`) makes this visible:

| Repo | Signature | % single-commit | % share one first-commit day | median commits | bulk-published |
|---|---|---|---|---|---|
| davila7/claude-code-templates | mega-collection | 100% | 50% | 1 | **yes** |
| BbgnsurfTech/...collection | mega-collection | 100% | 100% | 1 | **yes** |
| anthropics/skills | canonical | 61% | 89% | 1 | **yes** |
| openai/skills | canonical | 50% | 30% | 1.5 | no |
| mattpocock/skills | domain-pack | 35% | 55% | 3 | no |
| deanpeters/PM-Skills | domain-pack | 5% | 50% | 4 | no |
| affaan-m/ECC | mega-collection | 5% | 25% | 3 | no |
| wshobson/agents | marketplace | 0% | 30% | 4 | no |
| obra/superpowers | boutique | 0% | 100% (one launch day) | 9 | iterated in-repo |

The two purest mega-collections are **100% single-commit** — every skill landed in
one shot, zero in-repo revision. `anthropics/skills` is also a bulk publish (89%
share one day): a snapshot of internally-developed skills, so its git history
tells us nothing about how much each was iterated before release. At the other
end, `obra/superpowers` is genuinely worked *in* the repo (median 9 commits).

**Conclusion:** commit count is the wrong instrument. Where iteration happens
in-repo, it doesn't predict quality (corr ≈ 0); where it doesn't (bulk publishes,
including Anthropic and the mega-collections), the history can't measure maturity
in the first place. Quality is set by the **authoring standard at publish time**,
not by how the file was version-controlled. To probe true maturity you'd need a
signal outside git — e.g. an explicit `version:` field, or tracking a skill back
to its *origin* repo rather than the collection that copied it.

Data: `data/skill_maturity.json` (now includes `bulk_publish_by_repo`).

## The judgment axes (v3) — what the heuristic can't see

The judge was extended with three axes that map to the harder checklist items
(`scope`, `instruction`, `safety`). Across the 34-skill stratified sample
(`data/llm_sample_v2.json`), mean scores 0–10:

| Axis | Mean | Read |
|---|---|---|
| triggering | 5.6 | the known gap (when/anti-trigger) |
| **instruction** | **5.7** | **new — second-weakest; the heuristic is blind to it** |
| disclosure | 5.8 | inline-heavy bodies |
| frontmatter | 6.2 | |
| safety | 6.8 | moderate; a few sharp failures |
| structure | 6.9 | the corpus's strength |
| scope | 7.2 | most skills are reasonably narrow |
| tone | 7.3 | |

**Instruction quality is the new finding.** It's nearly as weak as triggering and
*completely invisible* to the structural scorer: skills that score 85–88
heuristically get `instruction=3` (e.g. `johnlindquist/design`,
`muratcankoylan/template`) — clear headings, ambiguous actual guidance. This is
exactly the heuristic-vs-judgment split: a regex can confirm a heading exists, not
that the instruction under it is unambiguous.

**Safety catches what high-stakes flags can't grade.**
`BbgnsurfTech/penetration-tester` scores 78 on the heuristic but **safety=1** — a
pen-testing skill with no validation, scoping, or guardrails. The heuristic flag
`high-stakes-no-safety` surfaces the candidate; the LLM confirms the severity.

Takeaway: the heuristic gate is necessary but the `instruction` and `safety` axes
are where the next round of real quality improvement lives — and neither is
fakeable with pattern-matching.
