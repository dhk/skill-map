# 6. Score sophistication as features behind a seven-level ladder

Date: 2026-11-26

## Status

Accepted

## Context

This repo found that only 2.5% of skills carry an anti-trigger ([STATS.md](../STATS.md), June 2026 crawl). The Atlas extends
that kind of finding into a trend: how sophisticated are skills, and is that
rising? A single score would hide which capabilities drive the change and
would freeze one weighting.

## Decision

Detect features per distinct skill text and present them as a ladder:

- **L0 Prompt in a file:** name, description, freeform text.
- **L1 Routed:** the description says what and when (WHEN-trigger).
- **L2 Bounded:** anti-trigger or scope limits, a stated output format,
  guardrails or ask-before-acting.
- **L3 Progressive disclosure:** a short body with `references/` loaded on
  demand.
- **L4 Tooled:** bundled scripts for deterministic steps, declared tools or MCP
  dependencies.
- **L5 Self-checking:** a verification step, error recovery, shipped evals.
- **L6 Composed:** hands off to other skills or subagents.

Features are stored in `sophistication_feature` with a detector version. The
ladder level is a view computed from them.

## Consequences

- Most features are detectable deterministically, which keeps scoring cheap
  and reproducible; LLM detection is used only where a rule cannot decide.
- The ladder can be re-weighted or redefined without re-running detectors.
- Existing rubric code in `crawlers/` is reused where it already detects a
  feature.
