# Quality by Skill Type

The same rubric, sliced by what a skill *is* (classified heuristically from its
name). After the parser fix (see the [correction note](what-i-learned-crawling-39-repos.md)),
the by-type spread is **much flatter than first reported** — the dramatic
"data/analytics is the worst type" finding was mostly the block-scalar artifact.

| Skill type | N skills | Median quality | % with WHEN-trigger |
|---|---|---|---|
| transformer/converter | 47 | 82.5 | 72% |
| generator/creator | 481 | 80.5 | 82% |
| other/domain | 2,881 | 80.0 | 66% |
| reviewer/auditor | 326 | 79.5 | 76% |
| reference/guide | 129 | 78.8 | 51% |
| data/analytics | 246 | 78.0 | 70% |
| test/quality | 232 | 78.0 | 68% |
| integration/connector | 138 | 78.0 | 71% |
| workflow/orchestrator | 422 | 78.0 | 66% |

## What the slice shows

**Type barely predicts quality.** Every type sits in a tight 78–82.5 band. Skill
*definition* quality is set by the repo's authoring discipline, not by the kind of
work the skill does. This mirrors the headline finding: the repo **signature**
(curated vs mega-collection) is the dominant predictor, not type, stars, recency,
or commits.

**The one consistent type signal is WHEN-trigger rate, and it's modest.**
`reference/guide` skills trigger worst (51%) — they're written as documents, so
authors forget the "use this when…" framing. `generator/creator` triggers best
(82%) because a concrete output makes the trigger obvious to write.

## Per-type guidance (what little there is)

- **reference/guide** → you're writing a doc; remember it's still a skill. Add an
  explicit "Use this when the user asks about X" trigger (only half of you do).
- **workflow / data / test / integration** → all cluster at 78 with ~70%
  triggers; the generic advice applies — add WHEN- and anti-triggers, push depth
  to reference files.
- **everyone** → the anti-trigger note is missing across all types (~97%); that's
  the universal win, not a type-specific one.

## Method note

Type is assigned by keyword-matching the skill name — a coarse cut
(`other/domain` catches 59% that don't match a verb pattern). Data lives in
`data/skill_types.json`.
