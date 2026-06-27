# Skill Definition Best Practices — the Anthropic Gold Standard, measured

This is the rubric the whole study is built on. It is **derived empirically
from the canonical reference skills** — `anthropics/skills` (18 skills) and
`openai/skills` (44 skills) — not invented. Every threshold below comes from
measuring what those repos actually do, then encoding it so any `SKILL.md` can
be scored automatically (`crawlers/skill_quality.py`).

The canonical repos validate the rubric: Anthropic scores a **median 87/100**,
OpenAI **89.5/100**. The one Anthropic skill that scores low (43) is the
intentional `template` stub — exactly what should score low.

---

## What the gold standard looks like (the measured facts)

| Trait | anthropics/skills | openai/skills |
|---|---|---|
| Always has `name` + `description` | 18/18 | 44/44 |
| Description length (median words) | 43 | 42 |
| Description states **when** to use it | 13/18 (72%) | 34/44 (77%) |
| Body length (median words) | ~1,194 | ~940 |
| Uses headings (`##`/`###`) | nearly all | nearly all |
| Links to reference files for depth | yes (e.g. `mcp-builder` → 10) | yes |
| Frontmatter beyond name/desc | `license` (15/18) | `metadata` (8/44) |

The throughline: **tight frontmatter, a description that says WHAT + WHEN, and
a body that uses progressive disclosure** (link out for depth instead of dumping
everything inline).

---

## The four scored dimensions

Each dimension scores 0–100; the overall is a weighted blend.

### 1. Frontmatter hygiene — 25%
- `name` present and a valid slug (`lowercase-with-hyphens`)
- `description` present
- valid YAML frontmatter delimiters
- `name` matches the skill's directory
- `license` or `metadata` present (canonical repos do this)
- no nonstandard/junk keys

### 2. Description triggering — 30% (the highest weight)
This is the single most important thing a skill definition does: it is the only
text Claude sees when *deciding whether to invoke the skill*. The gold standard
description states:
- **WHAT** the skill does (an action verb: "Creating…", "Converts…", "Reviews…")
- **WHEN** to use it (the "Use this when the user…" pattern)
- in a **healthy length** — long enough to disambiguate (~14–60 words), not a
  bloated paragraph

A description without a WHEN-trigger is the most common defect in the entire
corpus (see the study). It is also the cheapest to fix and the highest-leverage.

**The anti-trigger note.** The tuned LLM judge ([llm-judge-tuning.md](llm-judge-tuning.md))
surfaced one practice even the canonical skills usually skip: stating when *not*
to invoke the skill. `anthropics/skills/xlsx` does this well ("not for Word docs,
Google Sheets, or standalone scripts") and it measurably prevents false-positive
retrieval on adjacent tasks. A complete description states **what**, **when**, and
**when not**. The heuristic scorer doesn't yet require it; the judge does.

### 3. Progressive disclosure — 20%
- a real body (not a stub)
- **token economy**: a body over ~2,200 words with *zero* links to reference
  files is penalized — the canonical pattern is to push depth into separate
  files (`reference.md`, scripts) and keep `SKILL.md` navigable
- bonus for linking to reference files / scripts

### 4. Structure & examples — 25%
- headings (`##`/`###`)
- at least one concrete example or code block where appropriate
- bullets or numbered steps (procedural guidance)
- not a stub

---

## Grades

| Grade | Score | Meaning |
|---|---|---|
| A | ≥ 85 | Gold-standard quality |
| B | 70–84 | Solid, minor gaps |
| C | 55–69 | Usable but diverges noticeably |
| D | 40–54 | Significant gaps |
| F | < 40 | Broken / stub |

---

## Heuristics vs. judgment

The scorer measures **structure** — it can verify a description *has* a
when-clause, but not whether that clause is *good*. The LLM deep-read
(`crawlers/sample_llm.py`) covers the gap: it samples skills across the quality
range and asks Claude to compare each to the Anthropic house style. The two
disagree in instructive places — some skills that score well structurally read
as "weak" on substance (a skill can have perfect headings and still not earn its
place). Use the heuristic score as a fast gate and the LLM read as the tiebreak.

## Run it yourself

```bash
# score one skill
python crawlers/skill_quality.py path/to/SKILL.md

# audit a whole repo (local, or GitHub public/private with a token)
python crawlers/audit_repo.py ~/.claude/skills
python crawlers/audit_repo.py --github owner/repo --token $GITHUB_TOKEN
```
