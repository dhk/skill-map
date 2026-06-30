---
spec: "0.1"
type: workflow
name: skill-doctor-review
description: >
  Full skill review cycle: read the skill, interview the author, score it,
  recommend fixes, then apply them on confirmation.
license: MIT

steps:
  - id: read
    skill: skill-doctor
    description: Read the target SKILL.md and parse frontmatter, triggers, and body
    output: parsed skill structure

  - id: interview
    skill: skill-doctor
    description: >
      Run the structured interview — allowed-tools scoping, data sensitivity,
      high-stakes actions, triggering, install scope
    requires: [read]
    output: interview answers

  - id: score
    skill: skill-doctor
    description: Score against the 5-axis rubric using parsed content + interview answers
    requires: [read, interview]
    output: scored rubric with defect list

  - id: recommend
    skill: skill-doctor
    description: Produce ranked recommendations with specific edits
    requires: [score]
    output: edit recommendations

  - id: apply
    skill: skill-doctor
    description: Apply accepted edits to the SKILL.md in place
    requires: [recommend]
    guard:
      type: confirmation
      prompt: "Apply these edits to the file?"
    on_failure: leave file unchanged, surface error

on_failure: abort at the failing step, report what was completed
---

## Notes

All steps are performed by a single invocation of `skill-doctor` — this workflow
documents the internal structure of the skill's execution, not a multi-skill pipeline.
It is provided as a `WIRING.md` to make the step sequence machine-readable and to
demonstrate the spec format.
