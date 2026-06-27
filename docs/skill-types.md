# Quality by Skill Type

The same rubric, sliced by what a skill *is* (classified heuristically from its
name). This surfaces which **kinds** of skills the ecosystem writes well and
which it writes badly — independent of which repo they live in.

| Skill type | N skills | Median quality | % with WHEN-trigger |
|---|---|---|---|
| transformer/converter | 47 | **80.0** | 46.8% |
| reference/guide | 129 | 78.0 | 44.2% |
| other/domain | 2,881 | 77.7 | 47.9% |
| generator/creator | 481 | 76.4 | 44.5% |
| workflow/orchestrator | 422 | 72.5 | 40.8% |
| integration/connector | 138 | 70.8 | 32.6% |
| reviewer/auditor | 326 | 68.9 | 32.5% |
| test/quality | 232 | 66.2 | 28.9% |
| **data/analytics** | 246 | **63.5** | **19.9%** |

## What the slice shows

**Output-shaped skills are written best.** `transformer/converter`,
`reference/guide`, and `generator/creator` — skills with a concrete, tangible
output — score highest. The author knows exactly what the skill produces, so the
description writes itself.

**Process-shaped skills are written worst.** `data/analytics`, `test/quality`,
and `reviewer/auditor` sit at the bottom. These are *judgment* skills — "review
this," "test that," "analyze the data" — and their descriptions are vaguest about
**when** to fire. `data/analytics` is the standout failure: **only 20% carry a
WHEN-trigger**, less than half the rate of generator skills.

**The WHEN-trigger gap tracks type, not just repo.** The bottom four types are
exactly the four with sub-33% trigger rates. A "code-reviewer" skill that doesn't
say *when* to review is nearly useless for retrieval — Claude can't tell it apart
from ten other reviewers.

## Per-type guidance

- **data/analytics, test/quality, reviewer/auditor** → your descriptions almost
  certainly under-specify the trigger. Rewrite to name the *situation*: "Use when
  the user asks to profile a dataset / before merging a PR / when reviewing
  Terraform." This is where the biggest, cheapest wins are.
- **integration/connector** → name the *system* in the trigger ("Use when
  connecting to Stripe / a Postgres database / a Slack workspace") so retrieval
  can match on the integration target.
- **generator/creator, transformer/converter** → already strong; tighten
  frontmatter and add reference files for the long ones.
- **reference/guide** → these are inherently long; make sure they use
  progressive disclosure rather than one giant wall.

## Method note

Type is assigned by keyword-matching the skill name (see the classifier in the
study's generation step). It's a coarse cut — `other/domain` (59% of skills)
catches everything that doesn't match a verb pattern — but the signal across the
typed buckets is consistent and large enough to act on. Data lives in
`data/skill_types.json`.
