# 4. Atlas scope: SKILL.md on GitHub and marketplaces, built on GitSkills

Date: 2026-11-26

## Status

Accepted

## Context

The Skill Concepts Atlas asks how purposes and concepts in published Claude
and ChatGPT skills spread and change over time and across settings. Public
"ChatGPT skills" use the same `SKILL.md` format as Claude skills (OpenAI's
plugin docs and Help Center), and workspace skills are private, so the
observable population is `SKILL.md` files on GitHub and in marketplaces.

GitSkills (July 2026) already holds 3,797,117 `SKILL.md` occurrences across
282,200 repos. Skill Constellations adds a dated copy network built from it.
GitHub code-search counts are not usable as population sizes.

## Decision

- Corpus v1: public GitHub `SKILL.md` files plus the major marketplaces.
- Start from GitSkills, pinned to one Zenodo version, and the existing Skill
  Map snapshots; add our own delta crawl for August to November 2026.
- Exclude Custom GPTs from v1. Treat AGENTS.md, CLAUDE.md, Cursor rules and
  Copilot instructions as a later sibling study.
- All work lives in this repository. Write-ups may move to a separate
  publication repo later.
- Produce the exposition (catalogue and labels) before the timeline.

## Consequences

- Phase 1 depends on GitSkills' terms. Because it states no license, the Atlas
  republishes its pointers and our derived labels, not its file contents.
- The delta crawl reuses `crawlers/crawl.py` and adds license detection.
- Pre-October-2025 history is out of scope until the sibling study.
