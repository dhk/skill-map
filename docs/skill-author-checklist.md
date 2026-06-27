# Skill Author Checklist — and where each item is measured

A practical checklist for writing a Claude skill. Each item is tagged with **how
it's checked** in this project's tooling, so you can see what a machine can verify
versus what needs a human or an LLM read:

- 🟢 **heuristic** — `crawlers/skill_quality.py` scores or flags it automatically
- 🔵 **LLM judge** — `crawlers/judge_llm.py` assesses it (needs real judgment)
- ⚪ **human** — only you can confirm it (process / runtime / taste)

A rule of thumb: *if someone can read the skill in a minute and understand exactly
when to use it, what it does, and what output it produces, it's probably in good
shape.*

## Scope
- ⚪🔵 The skill has one clear job.  *(LLM `scope` axis)*
- 🟢 The trigger is specific and easy to recognize.  *(triggering axis / `no-when-trigger`)*
- 🟢🔵 It does not overlap heavily with another skill.  *(auditor `find_overlap` intra-repo; LLM `scope`)*
- 🔵 It is narrow enough to be reliable, not a catch-all.  *(LLM `scope`)*

## Instruction quality
- 🔵 Top-level instructions are short and unambiguous.  *(LLM `instruction` axis)*
- 🔵 Says what to do, not just what to avoid.  *(LLM `instruction`)*
- 🟢 The desired output format is explicit.  *(flag `output-format-unstated`)*
- 🔵 Special constraints are stated early.  *(LLM `instruction`)*

## Structure
- 🟢 Essentials in the main skill file.  *(structure axis)*
- 🟢 Examples, edge cases, reference material in supporting files.  *(disclosure axis / `no-progressive-disclosure`)*
- 🟢 The main file is easy to scan.  *(structure: headings/bullets)*
- ⚪ Related files are logically named.

## Discoverability
- 🟢 Clear, descriptive, slug-style name.  *(frontmatter axis / `non-slug-name`)*
- 🟢 Description states **when** to use it.  *(triggering axis — our highest weight)*
- 🟢 The "right time to use this" is obvious; plus **when NOT to** (anti-trigger).  *(`no-when-trigger` / `no-anti-trigger`)*
- 🔵 No vague wording that forces the model to guess.  *(LLM `triggering`)*

## Control and safety
- 🟢 Marked user-invoked when model-triggering would be risky.  *(frontmatter `disable-model-invocation`)*
- 🟢🔵 Tight constraints / validation for high-stakes workflows.  *(flag `high-stakes-no-safety`; LLM `safety` axis)*
- 🔵 Validation steps where errors matter.  *(LLM `safety`)*
- ⚪ Prefer scripts / deterministic steps for fragile operations.

## Examples and validation
- 🟢 One or two good examples if output format matters.  *(structure: code blocks)*
- ⚪ Tested on real tasks, not just ideal cases.
- ⚪ Checked against edge cases and partial inputs.
- ⚪ Revised based on observed failure modes.

## Maintenance
- ⚪ Outdated instructions removed promptly.
- ⚪ Dependencies and references current.
- 🟢 Consistent naming/formatting across skills.  *(frontmatter consistency)*
- 🟢🔵 Periodically checked for overlap with newer skills.  *(auditor `find_overlap`)*

---

## What this tells you about the tooling

Roughly **half** the checklist is machine-verifiable (🟢) — that's the heuristic
scorer, and it's the fast gate. A big chunk needs **judgment** (🔵) — scope,
instruction clarity, safety adequacy — which is exactly what the LLM judge is for,
and why we don't fake it with brittle regexes. The rest (⚪) is **process and
runtime** — was it tested, is it maintained — which no static analysis can see
(and which the bulk-publish finding showed git history can't reliably reveal
either).

Run both layers on your own repo:

```bash
python crawlers/audit_repo.py ~/.claude/skills   # heuristic: scores, flags, overlap
python crawlers/judge_llm.py --validate          # LLM: scope/instruction/safety axes
```

See [best-practices.md](best-practices.md) for the measured rubric and
[update-from-anthropic.md](update-from-anthropic.md) for where even the canonical
skills miss a checklist item.
