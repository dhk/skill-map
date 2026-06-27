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

Run on the canonical repos (62 skills), the answer is clear — and it's a *null*
result:

| Metric | Value |
|---|---|
| corr(commit count, quality) | **−0.14** (negligible, slightly negative) |
| median commits per skill | 2 |
| mean quality, ≤median commits | 88.4 |
| mean quality, >median commits | 85.3 |

**More commits do not mean better definitions.** The canonical skills are mostly
written well *once* (median 2 commits) and rarely revised; the high-commit ones
are if anything marginally worse (revision churn ≠ polish). Quality comes from
the authoring standard, not from iteration count — consistent with the
repo-level finding that stars and recency don't predict quality either.

Caveat: the canonical set has little quality variance (everything is 80–100), so
the dynamic range is narrow. To test across the full A–F range, run
`maturity_crawl.py --all` (one API call per skill, ~4,900 calls — use a token).
Data: `data/skill_maturity.json`.
