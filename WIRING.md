---
spec: "0.1"
type: ensemble
name: skill-map-tools
description: >
  The skill-map toolset for skill authors: review a single skill interactively,
  audit a whole repo against the corpus, and submit it to the map.
license: MIT

entry: skill-doctor

members:
  - skill: skill-doctor
    role: >
      Interactive best-practice reviewer for a single SKILL.md. Interviews the
      author, scores against the rubric, and applies fixes on confirmation.

  - skill: skill-audit
    repo: dhk/skill-map
    role: >
      Repo-level auditor. Scores every skill in a repository, benchmarks against
      same-type peers in the corpus, and surfaces the worst offenders.
    optional: true

install:
  method: plugin
  source: plugins/skill-doctor
---

## Notes

`skill-doctor` is the entry point for individual skill review. `skill-audit` is
the GitHub Action / CLI path for whole-repo grading — it runs separately, not as
part of a sequence.

To install `skill-doctor` in Claude Code:
```
/plugin marketplace add dhk/skill-map
/plugin install skill-doctor@skill-map
```

See [SKILL-DOCTOR.md](SKILL-DOCTOR.md) for all install options.
See [WIRING-SPEC.md](WIRING-SPEC.md) for the full specification.
