# CLAUDE.md

The Skill Map: an interactive ecosystem map plus a crawled research
corpus over the Agent Skills ecosystem, plus skill-doctor (an installable
SKILL.md reviewer derived from the same evidence). Full orientation:
[README.md](README.md). Documentation index (architecture, generated
evidence, guides): [docs/README.md](docs/README.md) — keep that index in
sync whenever a new `docs/` subfolder is added, rather than leaving it to
go stale.

## Working rules

- Generated documents (`STATS.md`, `adopted-conventions.md`,
  `originators.md`, `curiosities.md`, `skill-wiring-study.md`, ...) name
  their generator in docs/README.md's table — regenerate via
  `crawlers/run_pipeline.py`, never hand-edit.
- Start architecture changes from
  [docs/architecture/overview.md](docs/architecture/overview.md) before
  touching boundaries between the site, crawler, corpus, and skill-doctor.
- `.claude/skills/skill-doctor` is the packaged skill this repo ships —
  see [SKILL-DOCTOR.md](SKILL-DOCTOR.md) for install/usage, not this file.
