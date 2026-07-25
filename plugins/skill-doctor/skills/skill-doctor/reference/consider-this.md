# Consider this (open questions, not scored)

A holding area for tensions and forward-looking ideas that came from real
usage but aren't resolved into the rubric yet. Revisit these when a new model
generation ships, when there's more data, or when someone pushes back on one.
Nothing here should be treated as a scored check.

## Noise complaints: anti-trigger and output-format
Real feedback, paraphrased, from someone running an auditor built on this
same rubric: they were seeing a lot of `no-anti-trigger` and
`output-format-unstated` findings that didn't feel necessary, and asked what
they were missing. The honest answer at the time was: not much — both checks
were being applied blanket-style regardless of whether the skill actually had
an ambiguous neighbor or a structured deliverable. `rubric.md` §2 and §4 now
make both checks contextual instead of universal. Keep watching the other
direction too — if this swings too far toward leniency, real ambiguity cases
could start going uncaught. If complaints shift from "too much noise" to
"missed an obvious collision," tighten back up.

## Skills maintenance across model generations
The same feedback raised something bigger than either individual check:
"skills maintenance" is a recurring task, not a one-time setup cost — every
time a new model generation ships, it's worth re-auditing `AGENTS.md` and
skills to check whether they're still needed, and whether they're more
explicit or rigid than the current model actually requires. A skill written
to compensate for an older, less capable model's weaknesses can turn into
unnecessary scaffolding — or actively counterproductive over-constraint —
once the underlying model improves and would have handled the ambiguity fine
on its own.

skill-doctor doesn't check this at all right now — it has no notion of
"which model generation was this instruction written for" or "has baseline
model capability moved past the need for this much explicitness." A
lightweight staleness signal is worth exploring: e.g., flagging skills whose
instructions read as heavy-handed compensation for limitations (rigid
step-by-step scaffolding for tasks a current model could reasonably
improvise) and suggesting a fresh look rather than assuming the original
rigor is still warranted.

## Repo-context-aware suggestions
Adjacent feedback — more about the crawler-based `skill-audit` GitHub Action
than skill-doctor itself, but worth carrying over since they share a rubric
and users: "Top 10 general-purpose skills you're missing"-style output that
ignores what the repo actually does (recommending `seo-audit` or
`brand-guidelines` to an API-only backend repo) reads as noise, not help.
If skill-doctor — or anything built on this rubric — ever recommends
adopting *other* skills, not just fixing the one under review, that
recommendation needs to be conditioned on what the repo actually is, not a
flat popularity ranking across the whole corpus.

## Static analysis vs. empirical testing (genuinely open)
skill-doctor is purely static — it reads the `SKILL.md` text and never runs
it. Anthropic's own `skill-creator` is empirical — it runs test prompts
with-skill and without-skill and compares real outputs. A skill can score
well here and still underperform in practice, or score poorly here and work
great in practice. The "doesn't look like it went through skill-creator"
signal in rubric.md §4 (second-person voice, first-person description,
non-standard anatomy) is a *proxy* for "was this empirically tested" — it is
not a measurement of it. Expect false positives (excellent hand-written
skills that trip the voice heuristic) and false negatives
(skill-creator-shaped skills that still don't perform well). Don't over-trust
it, and don't present it as more than a "worth a look" nudge.
