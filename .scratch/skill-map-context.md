# Skill Map — Session Context Snapshot

**Date:** June 2026  
**Repo:** github.com/dhk/skill-map  
**Live:** dhk.github.io/skill-map  
**Status:** shipped, all code pushed to main

---

## What this is

An interactive force-directed map of 1,119 published Claude Code skills across 52 orgs and 13 domains, crawled from VoltAgent/awesome-agent-skills in June 2026. The main argument: the ecosystem has deeply covered the task layer, but five territories have zero published skills — the most important being the Session Layer, where DHK has 8 production skills and no public competition.

The map is an outreach artefact as much as a tool. Its purpose is to make the gap visible and establish DHK's credibility in the space.

---

## Architecture

Single self-contained `index.html`. No build step. D3.js v7 (CDN) for the force-directed graph, PapaParse (CDN) for CSV. SEED_DATA sentinel pattern: `const SEED_DATA = null` gets replaced with graph JSON at export time.

**Graph data:** 226 nodes, 302 links. Structure: domain nodes → org nodes → skill nodes, with negative space "uncharted territory" clouds rendered as SVG ellipses in the blank areas around the main graph cluster.

---

## Key features built this session

**Filter accumulator:** click any node (domain, org, skill, DHK hub, uncharted cloud) to add it to a pending filter. Filters accumulate in a bar below the controls. "Apply Filter" resolves each filter item to the relevant node set and shows only those nodes + their connections. "Clear" resets to full graph.

**Install panel:** slide-out panel listing all currently-visible skill nodes. Users can select individual skills or "Select All" (respects active text filter — only selects visible rows). Generates `git clone https://github.com/${id} ~/.claude/skills/${id.split('/')[1]}` commands per skill. Includes note that no unified registry exists yet.

**Uncharted territory clouds:** SVG ellipses (`rx=70, ry=36`) in negative space. Fill `#fef2f2`, stroke `#dc2626` (2.5px), dashed (`8,4`), red drop-shadow glow. Clickable — opens a panel describing that territory.

**Live links throughout:** org panels link to github.com/orgSlug, skill panels link to the org and repo, DHK hub links to www.dhk.io, davehk@gmail.com, Substack, and the skill-map repo itself.

**Panel slide-out:** `position: fixed; right: 0; transform: translateX(100%)` → `.open { transform: translateX(0) }`. Controls shift left when panel opens (`#controls.panel-open { right: 364px }`).

**Design system:** DHK palette applied. `--bg: #f9f8f6`, `--bg2: #f2f1ee`, `--accent: #16a34a`, `--text-dim: #5a5850`. Barlow Condensed headings, Barlow 300 body, DM Mono metadata/links. Light mode throughout.

**Search:** case-insensitive (`q.toLowerCase()` matched against lowercased node text).

**PUBLISHED SKILLS label:** renamed from "CLUSTER SIZE" — now reads "X skills tagged to this domain in awesome-agent-skills (the full 1,119-skill dataset this map is built from)" with a link to the source repo.

---

## Files

```
index.html                        main artefact, all features
README.md                         DHK voice, links to live map, Substack, GitHub
data/
  graph_data_v2.json              226 nodes, 302 links (extracted from HTML)
  personas.json                   13 personas
docs/
  internal-skill-map.md          design doc: how to point crawler at corporate GitHub
drafts/
  substack-draft.md              ~900 words, "The Session Layer", ready to publish
  tweet-thread.txt               6 tweets, all ≤280 chars, tags @simonw in tweet 2
  pull-quotes.txt                3 pull quotes for outreach
  image-instructions.txt         hero image prompts
outreach/
  dhk-session-layer.docx        door-opener doc (needs live URL added — see below)
validation.txt                   checklist
.claude/
  launch.json                    skill-map server: npx serve -p 4321
```

---

## Git state

Last commit: `7d1b74f — docs: internal skill map design doc`  
Branch: `main`, up to date with origin.

Commit history this session (newest first):
- `7d1b74f` docs: internal skill map design doc
- `a149315` style: stronger uncharted territory borders
- `7e8e712` feat: SELECT ALL button in install panel
- `642ae60` fix: clarify CLUSTER SIZE label
- `7d712cd` feat: filter accumulator
- (earlier: light mode, panel fix, live links, install panel, NS clouds)

---

## Outstanding tasks

### Needs DHK (human):
- Verify live map at dhk.github.io/skill-map (Pages should be built)
- Update `outreach/dhk-session-layer.docx` with live URL `dhk.github.io/skill-map`, export to PDF
- Take screenshots for outreach package (Phase 5 — Playwright or manual)
- Publish Substack draft (`drafts/substack-draft.md`)
- Post tweet thread (`drafts/tweet-thread.txt`)
- Submit PR to VoltAgent/awesome-agent-skills

### Known minor issues (deferred):
- Domain panel "FOLLOWS" tags run together without separators ("Playwright changelogtesting-library docs") — cosmetic, low priority

---

## DHK's session-layer skills (8 in production)

captain's-log, close-day, plan-day, reading-list-builder, daily-briefing, snapshot-create, tricorder, weekly-reset.

All pre-date Anthropic's October 2025 formalization of the Skills format. None appear in the public corpus. This is the core credential behind the outreach.

---

## Context for next conversation

The map is complete and live. The outreach package (doc, Substack draft, tweet thread) is written. What remains is publishing: update the docx with the live URL, take screenshots, publish to Substack, post tweets, submit to awesome-agent-skills.

The internal-skill-map design doc (`docs/internal-skill-map.md`) is the B2B angle: a Python crawler + nightly GitHub Actions workflow that builds the same map for a corporate GitHub org. The session layer gap shows up there too — most internal corpora mirror the public pattern.
