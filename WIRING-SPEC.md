# WIRING.md Specification

**Version:** 0.1.0  
**Status:** Draft  
**Maintained by:** [dhk/skill-map](https://github.com/dhk/skill-map)

A convention for declaring how Claude Agent Skills compose into flows, routers, and ensembles. Machine-readable. Human-auditable. No runtime required.

---

## Motivation

The skill corpus contains thousands of implicit inter-skill references — slash-command invocations, sequential cues, named dependencies — that exist only in prose. `WIRING.md` makes that layer explicit so it can be indexed, validated, and reasoned about.

See: [`docs/skill-wiring-study.md`](docs/skill-wiring-study.md) for the corpus evidence.

---

## File placement

| Scope | Path |
|---|---|
| Skill-level flow | `skills/<name>/WIRING.md` — alongside `SKILL.md` |
| Repo-level flow | `wiring/<flow-name>/WIRING.md` |
| Repo-level ensemble | `WIRING.md` at repo root |

A repo may contain multiple `WIRING.md` files. Each describes one flow or ensemble.

---

## Format

YAML front-matter only — no Markdown body required (though prose notes are welcome below the YAML block). The front-matter is delimited by `---` as in `SKILL.md`.

```
---
<fields>
---

Optional prose notes.
```

---

## Required fields

Every `WIRING.md` must include these three fields:

| Field | Type | Description |
|---|---|---|
| `spec` | string | Spec version this file targets. Currently `"0.1"`. |
| `type` | enum | `router` \| `workflow` \| `ensemble` |
| `name` | string | Slug identifier. Lowercase, hyphens only. |

---

## Type: `router`

Routes an incoming request to one or more skills based on intent. The router
reads the request, selects the appropriate sub-skill(s), and optionally synthesizes
their outputs.

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `spec` | string | yes | `"0.1"` |
| `type` | string | yes | `"router"` |
| `name` | string | yes | Slug for this router |
| `description` | string | yes | One sentence: what it routes and when to use it |
| `entry` | string | yes | Skill that performs the routing (must be in `routes` or installed) |
| `routes` | list | yes | Routing table — see below |
| `context` | object | no | Shared context the router loads before routing — see below |
| `synthesis` | string | no | How outputs from parallel routes are combined |
| `license` | string | no | SPDX identifier |

#### `routes[]` fields

| Field | Type | Required | Description |
|---|---|---|---|
| `trigger` | string | yes | Plain-language description of what request pattern activates this route |
| `skill` | string | no* | Single skill to invoke |
| `skills` | list | no* | Multiple skills to invoke |
| `mode` | enum | no | `sequential` (default) \| `parallel` |
| `repo` | string | no | `owner/repo` if skill lives in another repository |

*One of `skill` or `skills` is required per route.

#### `context` fields

| Field | Type | Description |
|---|---|---|
| `requires_file` | string | Path to a context file the router reads before routing |
| `missing_action` | string | What to do if `requires_file` is absent |

### Example

```yaml
---
spec: "0.1"
type: router
name: marketing-ops
description: Routes marketing questions to the right specialist skill.
license: MIT

entry: marketing-ops

context:
  requires_file: .claude/product-marketing-context.md
  missing_action: Run the marketing-context skill first to create context.

routes:
  - trigger: "SEO, search rankings, organic traffic"
    skill: seo-audit

  - trigger: "campaign planning, paid ads, channel mix"
    skill: marketing-campaign

  - trigger: "landing page, conversion, CRO"
    skill: landing

  - trigger: "brand, tone, voice, guidelines"
    skill: brand-guidelines

  - trigger: "full campaign orchestration across channels"
    skills: [marketing-campaign, seo-audit, landing, social-content]
    mode: parallel

synthesis: Summarize outputs per skill, then provide a unified recommendation.
---
```

---

## Type: `workflow`

An ordered sequence of steps. Each step may invoke a skill, pass output to the
next step, and gate on a condition before proceeding.

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `spec` | string | yes | `"0.1"` |
| `type` | string | yes | `"workflow"` |
| `name` | string | yes | Slug for this workflow |
| `description` | string | yes | One sentence: what it produces and when to use it |
| `steps` | list | yes | Ordered steps — see below |
| `on_failure` | string | no | Default failure behavior across all steps |
| `license` | string | no | SPDX identifier |

#### `steps[]` fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique slug within this workflow |
| `skill` | string | yes | Skill to invoke at this step |
| `repo` | string | no | `owner/repo` if skill is external |
| `description` | string | no | What this step does |
| `requires` | list | no | IDs of steps that must complete before this one |
| `input` | string | no | What this step consumes from prior steps |
| `output` | string | no | What this step produces (file path, object name, or description) |
| `guard` | object | no | Condition before proceeding — see below |
| `on_failure` | string | no | Step-level failure behavior (overrides workflow-level) |

#### `guard` fields

| Field | Type | Description |
|---|---|---|
| `type` | enum | `confirmation` \| `dry_run` \| `condition` |
| `prompt` | string | For `confirmation`: the question to ask the user |
| `flag` | string | For `dry_run`: the CLI flag to pass |
| `check` | string | For `condition`: expression that must be true to proceed |

### Example

```yaml
---
spec: "0.1"
type: workflow
name: skill-review-and-publish
description: >
  Full skill authoring pipeline: review an existing skill, apply fixes,
  audit the repo, then publish.
license: MIT

steps:
  - id: review
    skill: skill-doctor
    description: Interview-based review and fix of a single SKILL.md
    output: reviewed SKILL.md in place

  - id: audit
    skill: skill-audit
    description: Score the full repo and benchmark against peers
    requires: [review]
    output: audit report

  - id: publish
    skill: git-workflow
    description: Commit, tag, and push
    requires: [audit]
    guard:
      type: confirmation
      prompt: "Audit passed. Commit and push?"
    on_failure: abort and surface error
---
```

---

## Type: `ensemble`

A named collection of skills installed and used together. No fixed execution
sequence — members are invoked on demand. An optional `entry` skill acts as
a coordinator or router across members.

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `spec` | string | yes | `"0.1"` |
| `type` | string | yes | `"ensemble"` |
| `name` | string | yes | Slug for this ensemble |
| `description` | string | yes | One sentence: what the ensemble provides |
| `members` | list | yes | Member skills — see below |
| `entry` | string | no | Skill that coordinates the ensemble (must be in `members`) |
| `install` | object | no | Installation instructions — see below |
| `license` | string | no | SPDX identifier |

#### `members[]` fields

| Field | Type | Required | Description |
|---|---|---|---|
| `skill` | string | yes | Skill name |
| `repo` | string | no | `owner/repo` if external |
| `role` | string | no | What this member does within the ensemble |
| `optional` | boolean | no | Whether this member can be omitted. Default: `false` |

#### `install` fields

| Field | Type | Description |
|---|---|---|
| `method` | enum | `symlink` \| `copy` \| `plugin` |
| `target` | string | Destination path |
| `source` | string | Source path within this repo |

### Example

```yaml
---
spec: "0.1"
type: ensemble
name: skill-map-tools
description: >
  The skill-map toolset: review a single skill, audit a whole repo,
  and submit it to the map.
license: MIT

entry: skill-doctor

members:
  - skill: skill-doctor
    role: Interactive best-practice reviewer for a single SKILL.md
  - skill: skill-audit
    repo: dhk/skill-map
    role: Repo-level auditor with peer benchmarking
    optional: true

install:
  method: plugin
  source: plugins/skill-doctor
---
```

---

## Cross-repo skill references

When a skill lives in another repository, qualify the `skill` field with `repo`:

```yaml
steps:
  - id: review
    skill: skill-doctor
    repo: dhk/skill-map
```

Or inline as `owner/repo/skill-name` shorthand (tools that support it):

```yaml
skill: dhk/skill-map/skill-doctor
```

Unqualified names are resolved in order:
1. Same repo
2. `~/.claude/skills/` (locally installed)
3. Unresolvable — validator flags as a warning, not an error

---

## Validation

Run the bundled validator:

```bash
python crawlers/validate_wiring.py path/to/WIRING.md
```

Or as a GitHub Action on any PR that touches a `WIRING.md`:

```yaml
- uses: dhk/skill-map/.github/actions/skill-audit@main
  with:
    validate_wiring: true
```

Exit codes: `0` valid · `1` schema error · `2` broken skill reference.

---

## Minimal valid files

**Router (5 lines):**
```yaml
---
spec: "0.1"
type: router
name: my-router
description: Routes X to the right skill.
entry: my-router
routes:
  - trigger: "anything"
    skill: my-skill
---
```

**Workflow (5 lines):**
```yaml
---
spec: "0.1"
type: workflow
name: my-workflow
description: Does X then Y.
steps:
  - id: step-a
    skill: skill-a
  - id: step-b
    skill: skill-b
    requires: [step-a]
---
```

**Ensemble (5 lines):**
```yaml
---
spec: "0.1"
type: ensemble
name: my-ensemble
description: A set of skills for X.
members:
  - skill: skill-a
  - skill: skill-b
---
```

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| 0.1.0 | 2026-06-30 | Initial draft. Three types: router, workflow, ensemble. |

---

## Contributing

Open an [issue](https://github.com/dhk/skill-map/issues) with:
- A `WIRING.md` pattern the spec can't express
- A field name or structure that's unclear
- A real orchestrator skill from the corpus that doesn't fit any archetype

The spec will evolve toward v1.0 as real-world usage accumulates.
