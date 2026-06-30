# WIRING.md — A Convention for Declaring Inter-Skill Integration

*Proposed by DHK, grounded in corpus analysis of 4,953 published skills.*
*Status: draft v0.1 — feedback welcome via [GitHub issues](https://github.com/dhk/skill-map/issues).*

---

## Why this exists

The skill corpus already contains an implicit wiring layer. Discovery against 3,815
skills with full content found **4,477 explicit cross-skill references** — slash-command
invocations, sequential cues, and named dependencies — including **2,425 cross-repo
edges** where a skill in one repository references a skill published in another.

None of this is machine-readable. A coordinator skill like `marketing-ops` names six
sub-skills in its body prose. A workflow skill like `mle-workflow` declares a sequence
of steps, each implying a different skill. An installer like `configure-ecc` selects
from a catalog at runtime. In every case, the wiring exists — it's just undeclared.

`WIRING.md` makes it explicit.

---

## What `WIRING.md` is

A `WIRING.md` file lives alongside `SKILL.md` in a skill's directory (or at the
repo root for a repo-level flow). It declares:

- what **type** of integration this is (router, workflow, or ensemble)
- which **skills** are involved, and from where
- what **passes between** them (context, output, handoff)
- what **guards** apply (confirmation steps, preconditions, failure paths)

It is plain YAML + Markdown — the same format discipline as `SKILL.md`. No runtime
required. A human reading it understands the flow; a crawler can index it; a future
toolchain can validate it.

---

## Three archetypes from the corpus

Derived from real orchestrator skills in the wild.

### 1. Router

Reads intent, routes to one or more sub-skills, synthesizes output. The
sub-skills are independent; the router is the only coordinator.

*Corpus examples: `chief-of-staff`, `marketing-ops`, `engineering-advanced-skills`.*

```yaml
# WIRING.md
type: router
name: marketing-ops
description: >
  Routes marketing questions to the right specialist skill. Coordinates
  multi-skill campaigns across content, SEO, CRO, channels, and analytics.

entry: marketing-ops

routes:
  - trigger: "SEO, search rankings, organic traffic"
    skill: seo-audit
  - trigger: "campaign planning, paid ads, channel mix"
    skill: marketing-campaign
  - trigger: "landing page, conversion rate"
    skill: landing
  - trigger: "brand, voice, guidelines"
    skill: brand-guidelines
  - trigger: "multi-channel campaign orchestration"
    skills: [marketing-campaign, seo-audit, landing, social-content]
    mode: parallel

context:
  requires_file: .claude/product-marketing-context.md
  missing_action: "Run marketing-context skill first"
```

### 2. Workflow

A declared sequence of steps. Each step may invoke a different skill, pass
output forward, and gate on a condition. Steps are ordered; the sequence is
the deliverable.

*Corpus examples: `mle-workflow`, `subagent-driven-development`, `tdd-workflow`.*

```yaml
# WIRING.md
type: workflow
name: ml-production-pipeline
description: >
  End-to-end production ML workflow: data contracts → training → evaluation →
  deployment → monitoring.

steps:
  - id: data-contract
    skill: database-designer
    description: Define data schema and feature contracts
    output: data_contract.md

  - id: training
    skill: mle-workflow
    description: Reproducible training pipeline
    requires: [data-contract]
    output: model_artifact/

  - id: evaluation
    skill: model-evaluation-suite
    description: Offline eval against quality gates
    requires: [training]
    guard:
      type: confirmation
      prompt: "Eval passed — proceed to deployment?"

  - id: deployment
    skill: deployment
    description: Canary deploy with rollback path
    requires: [evaluation]
    guard:
      type: dry_run
      flag: --dry-run

  - id: monitoring
    skill: observability-designer
    description: SLOs, drift detection, alerting
    requires: [deployment]

on_failure: rollback to previous step and surface error
```

### 3. Ensemble

A named collection of skills that are installed and used together, without
a fixed sequence. The ensemble defines the ecosystem; individual skills are
invoked on demand.

*Corpus examples: `configure-ecc`, `c-level-skills`, `senior-backend`.*

```yaml
# WIRING.md
type: ensemble
name: c-level-advisory
description: >
  Full C-suite advisory layer. Skills are invoked independently on demand;
  chief-of-staff routes across them.

entry: chief-of-staff

members:
  - skill: ceo-advisor
    role: "Founder strategy, fundraising, board dynamics"
  - skill: cto-advisor
    role: "Architecture, engineering org, technical decisions"
  - skill: cfo-advisor
    role: "Burn, runway, financial modeling"
  - skill: cmo-advisor
    role: "Go-to-market, brand, growth"
  - skill: chief-of-staff
    role: "Orchestrator — routes questions to the right advisor"

install:
  method: symlink
  target: ~/.claude/skills/
  source: skills/c-level/
```

---

## Minimal valid `WIRING.md`

The full schema above is optional depth. A minimal declaration is:

```yaml
type: workflow          # router | workflow | ensemble
name: my-flow
description: One sentence.

steps:                  # or routes: or members: depending on type
  - skill: skill-a
  - skill: skill-b
```

That's enough for a crawler to index the dependency graph.

---

## Placement

| Scope | Location |
|---|---|
| Single-skill flow | `skills/my-skill/WIRING.md` (alongside `SKILL.md`) |
| Multi-skill repo flow | `wiring/my-flow/WIRING.md` |
| Repo-level ensemble | `WIRING.md` at repo root |

A repo may have multiple `WIRING.md` files — one per flow.

---

## Cross-repo skill references

Skills from other repos are referenced by `repo/skill-name`:

```yaml
steps:
  - skill: anthropics/skills/doc-coauthoring
  - skill: davila7/claude-code-templates/codex
  - skill: skill-doctor          # local (this repo)
```

If no repo prefix, the skill is assumed to be in the same repo or installed
in `~/.claude/skills/`.

---

## What this enables

**For authors:** declare intent explicitly. Stop hiding coordination logic in prose.

**For consumers:** know what a skill depends on before installing it. Audit a flow
before running it.

**For crawlers:** index the dependency graph. Detect cycles, missing dependencies,
cross-repo coupling.

**For tooling (future):** validate that declared skills exist, are installed, and
meet minimum quality standards before a flow runs.

---

## Relationship to `SKILL.md`

`WIRING.md` does not replace `SKILL.md`. Every skill in a flow still has its own
`SKILL.md` with its own trigger, rubric, and scope. `WIRING.md` declares how skills
compose — it is the layer above individual skills, not a replacement for them.

A skill that is *also* a coordinator (like `chief-of-staff`) has both:
- `SKILL.md` — its own invocation cue, safety scope, and workflow
- `WIRING.md` — the routing table and member list it orchestrates

---

## What we're asking

This is a proposed convention, not a standard. We are publishing it based on corpus
evidence of what authors are already doing implicitly, and inviting the community to:

1. **Try it** — add a `WIRING.md` to a skill or repo that has coordination logic.
2. **Give feedback** — open an [issue](https://github.com/dhk/skill-map/issues) with
   what the schema doesn't capture.
3. **Submit your repo** — the skill-map crawler will index `WIRING.md` files once the
   format stabilizes.

The goal is machine-readable wiring that matches what the corpus is already doing in
prose.

---

*Corpus data: `docs/skill-wiring-study.md`. Discovery script: `crawlers/discover_wiring.py`.*
*Related: `docs/skill-ecosystem-vulnerabilities.md` — quality and safety findings.*
