# 1. Distribute skill-doctor as a separate product, not just a folder in this repo

<!-- Retroactive ADR: this decision was already made and shipped (see commit
history: repo-free pip install, PyPI publish workflow, plugin marketplace
support, claude.ai zip build). Recorded after the fact so the reasoning isn't
lost, not proposing new work. -->

Date: 2026-07 (retroactively recorded; original changes landed across
several commits including #22, "Add repo-free pip install and automated
PyPI publishing for skill-doctor")

## Status

Accepted

## Context

skill-doctor (an interactive best-practice reviewer for a single SKILL.md)
and skill-audit (a repo-level version of the same scoring) share code with
the crawler/corpus pipeline (`skill_quality.py`, `repo_signature.py`). The
straightforward path was to tell users "clone this repo, symlink the skill
in" — but this repo also contains the full crawler, multi-GB-adjacent crawl
data, and unrelated research docs. A skill author who just wants to review
one `SKILL.md` shouldn't need any of that, and installing via full git clone
is a heavier, less trustworthy ask than a scoped package.

Claude Code, claude.ai, and the Desktop app also don't share one install
mechanism — plugins only work in Claude Code.

## Decision

Package skill-doctor as its own distributable unit
(`plugins/skill-doctor/`), independent of the crawler/data/docs that make up
the rest of the repo, and ship it through three channels matched to where a
user actually is:

- `pipx run dhk-skill-doctor` — a PyPI wheel with the skill content bundled
  as package data, no git required.
- Claude Code plugin marketplace (`dhk/skill-map` → `skill-doctor@skill-map`)
  — for users already inside Claude Code who want marketplace-managed
  updates.
- A prebuilt zip (`dist/skill-doctor.zip`) for claude.ai / Desktop, which
  don't support plugins at all.

All three pull from the same `plugins/skill-doctor/skills/skill-doctor/`
tree and carry the same version string in lockstep
(`plugin.json`/`pyproject.toml`), so they can't drift apart silently.

## Consequences

- A skill author gets a scoped install with no crawler/data/docs baggage,
  on whichever surface they're already using.
- Three distribution channels means three things to keep in version lockstep
  and three install-path failure modes to document (see `INSTALL.md`'s
  Troubleshooting section) — a real ongoing maintenance cost, accepted
  because the audience-fit gain outweighs it.
- skill-audit (the repo-level counterpart) stays inside this repo rather
  than being split out too, since it's meant to run against the corpus data
  that already lives here — only skill-doctor's single-skill review needed
  full independence.
