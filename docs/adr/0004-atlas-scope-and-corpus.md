# 4. Atlas scope: SKILL.md on GitHub and marketplaces, built on GitSkills

Date: 2026-11-26

## Status

Proposed. Becomes Accepted once DHK settles the open method decisions.

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
- Start from GitSkills, pinned to Zenodo version 1.0.0 (10 Aug 2026), and the existing Skill
  Map snapshots; add our own delta crawl for August to November 2026.
- Exclude Custom GPTs from v1. Treat AGENTS.md, CLAUDE.md, Cursor rules and
  Copilot instructions as a later sibling study.
- All work lives in this repository. Write-ups may move to Alexandria later.
- Produce the exposition (catalogue and labels) before the timeline.

## Consequences

- Zenodo v1.0.0 lists CC BY 4.0 for the whole GitSkills record, while its
  Hugging Face card says file text stays under each origin repository's
  license. Our reading follows the card: the Atlas credits GitSkills, reuses its
  metadata, republishes pointers and derived labels, and uses `repos.license`
  to decide where full text may be included.
- The delta crawl reuses `crawlers/crawl.py` and adds license detection.
- Pre-October-2025 history is out of scope until the sibling study.
