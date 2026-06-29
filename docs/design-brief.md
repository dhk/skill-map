# Skill Map — Design Brief for UX Review
**For:** Claude Design  
**From:** DHK  
**Date:** 2026-06-25  
**Purpose:** Request a UX spec for the next iteration of the skill map UI

---

## What This Is

A single-page web app that maps the public Claude agent skills corpus — ~4,975 SKILL.md files across 39+ GitHub repos — onto an interactive force-directed graph. Think of it as a **navigator for the skills ecosystem**: who published what, how skills cluster by domain, and how to find what you need.

Live at: `https://dhk.github.io/skill-map` (GitHub Pages, single `index.html`)  
Stack: D3 v7 force graph, vanilla JS/HTML/CSS, no framework, no build step.

---

## Current State of the UI

### Layout

One screen. No routing. Everything lives in a single viewport:

```
┌────────────────────────────────────────────────────────┐
│  SVG canvas (force-directed graph)          [PANEL →]  │
│                                                        │
│  [stats: N NODES · CLICK TO EXPLORE]                  │
│                                                        │
│  NODE FILTER bar (hidden until triggered)              │
├────────────────────────────────────────────────────────┤
│  BOTTOM BAR                                            │
│  [ALL][BY DOMAIN][CLUSTER][ORGS][SKILLS][DHK][UNCHARTED] │
│  [search pill box ············] [OR]  [MAP][LIST][INSTALL↗][+ADD] │
└────────────────────────────────────────────────────────┘
```

### Graph Nodes (6 types)

| Type | Count | Visual | Purpose |
|---|---|---|---|
| `domain` | 15 | Large colored circle | Category hub — Security, Frontend & UI, etc. |
| `org` | 53 | Small grey circle | GitHub org that published skills |
| `skill` | 149 | Tiny colored dot | Individual SKILL.md file |
| `dhk` | 8 | Green dot | DHK's personal/private skills |
| `dhk_hub` | 1 | Green circle | DHK session layer hub |
| `negative_space` | 5 | Faint cloud shape | "Uncharted" gaps — skill needs with no published skill |

### View Modes (bottom bar buttons)

- **ALL** — everything visible, default state
- **BY DOMAIN** — shows domain + skill nodes, dims orgs
- **CLUSTER** — toggle: fires a custom D3 force that pulls skills tightly toward their domain node
- **ORGS** — opens a panel listing all 53 orgs sorted by skill count
- **SKILLS** — shows only skill leaf nodes
- **DHK** — zooms to DHK's personal skill cluster
- **UNCHARTED** — zooms to negative space clouds

### Interaction Patterns

- **Click domain node** → side panel opens with persona card + skill count (clickable → filtered list) + unmet need
- **Click skill node** → side panel opens with description, domain, source URL, install checkbox
- **Click org node** → panel shows all skills from that org
- **Search bar** → live pill search (AND/OR toggle); accepts GitHub URLs (paste `https://github.com/getsentry` → filters to that org)
- **Node filter** → right-click type filter on nodes; creates a persistent highlight layer
- **MAP / LIST toggle** → list mode shows all skills as a table with checkboxes for install list
- **INSTALL ↗** → generates a `claude skills install` command for all checked skills
- **+ ADD** → modal to add a private/local skill (persisted to localStorage)

### Side Panel Content by Node Type

**Domain node panel:**
- Persona name + avatar + archetype quote
- "N skills in this domain" (clickable → list view filtered to domain)
- Persona description, what they use skills for, unmet need

**Skill node panel:**
- Label, domain, description
- Source URL (real GitHub link from crawl data, falls back to org page)
- ✓ IN INSTALL LIST / ＋ ADD TO INSTALL LIST toggle button

---

## Data Model

Each skill node now has **12 fields**:

```json
{
  "id": "getsentry/sentry-pr-code-review",
  "label": "sentry-pr-code-review",
  "type": "skill",
  "color": "#3b82f6",
  "size": 4,
  "org": "getsentry",
  "domain": "Developer Experience",
  "description": "Reviews PRs using Sentry context...",
  "source_url": "https://github.com/openai/skills/tree/main/skills/sentry-pr-code-review",
  "action": "analyze",
  "complexity": "intermediate",
  "output_type": "report",
  "integration": "connector"
}
```

### The 4 Ontology Dimensions (all 149 skills tagged)

| Dimension | Values | Distribution |
|---|---|---|
| **action** | generate · extract · transform · automate · analyze · configure · integrate | analyze 31, generate 31, configure 28, integrate 27, automate 19, transform 9, extract 4 |
| **complexity** | foundational · intermediate · advanced | intermediate 89, advanced 49, foundational 11 |
| **output_type** | text · code · structured-data · media · action · report | structured-data 41, code 31, action 29, report 27, media 13, text 8 |
| **integration** | standalone · connector · orchestrator · modifier | connector 59, standalone 53, orchestrator 26, modifier 11 |

### 15 Domains + Personas

| Domain | Color | Skills | Persona |
|---|---|---|---|
| Platform & APIs | indigo | 195 (curated: 30) | The Integration Engineer |
| Frontend & UI | violet | 128 | The Design Engineer |
| Developer Experience | blue | 81 | The Platform Engineer |
| Infrastructure & DevOps | sky | 82 | The Infrastructure Operator |
| Security | red | 76 | The Security Practitioner |
| Agent & Orchestration | amber | 70 | The Agentic Builder |
| Testing & Quality | cyan | 67 | The QA Practitioner |
| Document & Writing | pink | 58 | The Knowledge Worker |
| Data & Analytics | emerald | 65 | The Analytics Engineer |
| Creative & Media | orange | 52 | The Creative Technologist |
| Marketing & Growth | teal | 44 | The Growth Practitioner |
| Research & Learning | purple | 24 | The Deep Learner |
| Product & Strategy | lime | 33 | The Product Thinker |
| Finance & Payments | light-orange | 14 | The Fintech Builder |
| Session Layer | green | 8 | The Daily Practitioner (DHK) |

---

## Known UX Problems

### 1. Discoverability is broken
The graph looks impressive but doesn't help users find a skill they'd actually install. 149 dots with no filtering beyond keyword search. The 4 ontology dimensions exist in the data but are nowhere in the UI.

### 2. Bottom bar is cluttered
8 view buttons + search box + AND/OR toggle + MAP/LIST + INSTALL + ADD in one bar. No hierarchy. First-time users don't know what any of it does.

### 3. "BY DOMAIN" vs "CLUSTER" are confusing
Two separate buttons for related concepts. Users don't understand the difference between seeing domains vs clustering by domain.

### 4. The panel is doing too much
A single right panel handles: domain persona cards, skill detail cards, org lists, install list management. No visual differentiation between these modes.

### 5. List view is underutilised
The table is powerful (checkbox install, search filtering, domain filter) but hard to discover — it's behind a small MAP/LIST toggle. No way to sort by any dimension.

### 6. No onboarding
First-time visitor sees a graph with 231 unlabeled nodes. No hint of what to click, no sample query, no "start here."

### 7. Install flow is buried
The core value prop — "find skills and install them" — requires: search → click node → toggle install → repeat → click INSTALL ↗ → get CLI command. Too many steps, hard to discover.

### 8. Ontology dimensions have no UI
We have `action`, `complexity`, `output_type`, `integration` on every skill — but nothing in the UI surfaces them. Users can't filter by "show me all `generate` + `media` skills at `intermediate` complexity."

### 9. DHK layer is confusing to non-DHK users
DHK's personal skills + Session Layer domain are prominent in the graph but meaningless to anyone else visiting the map.

### 10. No mobile support
Canvas + bottom bar layout doesn't work on phone. All interactions assume desktop hover + click.

---

## What We'd Like from Design

### Primary Ask
A UX spec — wireframes or annotated mockups — for the next iteration. Focus on:

1. **Faceted navigation** using the 4 ontology dimensions as filter facets, alongside domain and org. The map should work like a good app store or package registry: browse by category, filter by type, search by keyword.

2. **Better first-run experience** — what does a first-time visitor see and do? What's the primary CTA?

3. **Simplified bottom bar** — reduce cognitive load. What's essential vs. secondary?

4. **Install flow** — make the "find → install" path obvious and short.

5. **Panel design** — how should domain persona cards, skill detail cards, and install list look distinct from each other?

### Secondary (if time)
- Mobile-first consideration (or at least "mobile acceptable")
- How to handle the DHK / Session Layer for non-DHK users (hide? de-emphasise?)
- Empty states (no search results, no skills in install list)

---

## Technical Constraints for Designer to Know

- **Single HTML file** — no React, no build step. Everything must be implementable as vanilla JS + CSS + D3.
- **D3 force graph** — the canvas is SVG; tooltips and panels are HTML overlays. Custom CSS variables (`--bg`, `--accent`, `--border`, etc.) control the dark theme.
- **No backend** — all data is embedded in the HTML as `const GRAPH = {...}`. No API calls at runtime (except GitHub links opening in new tabs).
- **GitHub Pages** — deployed from `main` branch root. Changes ship by pushing `index.html`.
- **The graph is the core** — the force simulation is the experience. Navigation modes should enhance graph exploration, not replace it.

---

## Reference Files

| File | What's in it |
|---|---|
| `index.html` | Entire app — HTML, CSS, JS, embedded GRAPH JSON |
| `data/skill_tags.json` | All 157 skill classifications (action, complexity, output_type, integration) |
| `data/graph_data_v2.json` | Source graph data before reclassify |
| `crawlers/crawl.py` | GitHub crawler — `run`, `local`, `list` subcommands |
| `crawlers/reclassify.py` | Rebuilds domain taxonomy from index.html JSON |
| `crawlers/enrich_urls.py` | Adds real source_url to skill nodes from crawl data |
| `crawlers/tag_skills.py` | Classifies skills via `claude -p` into 4 dimensions |
| `crawls/crawl-1-2026-06-24/` | Raw crawl data — 5,320 SKILL.md results from 39 repos |

---

## Tone / Aesthetic Reference

Current design is intentionally dense and terminal-adjacent: dark background (`#0f172a`), monospace type (`JetBrains Mono`), muted colors, minimal chrome. Feels like a developer tool. The design direction should stay in that register — **not** a marketing page, **not** a SaaS dashboard. Think: VS Code meets a force-directed graph, or `npm` search but spatial.

The DHK persona (Session Layer) is a personal layer — the map exists partly as a personal knowledge artefact and partly as a public exploration of the skills ecosystem. That duality should be preserved.
