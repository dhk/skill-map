---
list_id: seed-list-003
description: Aggregators, toolkits, and context tools surfaced from community roundup. Mostly discovery sources (awesome-* indexes) and tools rather than direct SKILL.md collections — mine the indexes for new repos, treat tools/prompt-registries accordingly.
created: 2026-06-27
strategy: repo-scoped
source: community-roundup
---

# Seed List 003 — aggregators, toolkits & context tools

Markdown crawl list. The crawler reads the table below (columns: **repo**,
**type**, **tier**, **notes**). All repos were existence-checked against the
GitHub API on 2026-06-27 before inclusion.

Types are honest about what's actually in each repo, because several are NOT
SKILL.md collections:
- `aggregator` / `index-only` — a curated list of *links*; mine it for repos, not skills.
- `toolkit` — mixed agents/skills/commands; has some real `SKILL.md` files.
- `prompt-registry` — prompts, not Agent Skills; out of scope for the quality rubric.
- `tool` — an MCP server / slash-command utility, not a skill collection.

| repo | type | tier | notes |
|---|---|---|---|
| rohitg00/awesome-claude-code-toolkit | toolkit | high-quality | 2.2k★. 135 agents, 35 curated skills, 42 commands. Has real SKILL.md files — crawl the skills/ subset. Notable: agento-patronum (secrets guard), skills-janitor (dedupe/audit). |
| quemsah/awesome-claude-plugins | aggregator | high-quality | 903★. Auto-tracked plugin adoption metrics — mine for trending repos, not skills directly. |
| langgptai/awesome-claude-prompts | prompt-registry | reference | 5.3k★. Prompt curation, not Agent Skills. Out of rubric scope; keep for discovery only. |
| mksglu/context-mode | tool | reference | 18k★. MCP server + slash commands for context optimization (ctx-stats/ctx-index/ctx-doctor). A tool, not a skill collection. |
