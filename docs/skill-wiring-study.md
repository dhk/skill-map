# Skill Wiring: Implicit Integration Patterns in the Corpus

*Discovered from 8,249 cross-skill references across the crawl corpus.*

---

## Overview

This study mines the skill corpus for implicit wiring: references from one skill's
body or description to another skill by name or slash-command. No new standard is
assumed — these are patterns that exist today, undeclared.

Three signal types were extracted:

| Signal | Edges found | Description |
|---|---|---|
| Slash-command reference (`/skill-name`) | 3,171 | Explicit invocation syntax in body |
| Sequential cue (after/before/requires) | 1,306 | Ordering language referencing a known skill |
| Known-name mention | 3,772 | Corpus skill name appearing in another skill's body |
| **Total** | **8,249** | |

---

## Key findings

**4,477 strong wiring edges** (slash-command or sequential cue) across the corpus.
**2,425 cross-repo edges** — skills in one repo referencing skills defined in another.
**1082 orchestrator candidates** — skills whose bodies contain coordination language
("coordinates", "chains", "pipeline", "handoff", "invokes").
**12 intra-repo clusters** — groups of 2+ skills that mutually reference each other.

---

## Most-referenced skills

Skills referenced most frequently by other skills — the hubs of the implicit wiring graph.

| Skill | Referenced by (edges) |
|---|---|
| `skill` | 222 |
| `best-practices` | 122 |
| `templates` | 121 |
| `search` | 115 |
| `new` | 107 |
| `database` | 85 |
| `service` | 72 |
| `generate` | 71 |
| `pre-commit` | 71 |
| `scikit-learn` | 70 |
| `everything-claude-code` | 69 |
| `deployment` | 65 |
| `coverage` | 65 |
| `code-reviewer` | 62 |
| `projects` | 59 |
| `metrics` | 57 |
| `template` | 57 |
| `status` | 57 |
| `review` | 55 |
| `performance` | 54 |

---

## Orchestrator candidates

Skills that contain explicit coordination language and reference two or more other skills.

| Orchestrator skill | References |
|---|---|
| `skill-adapter` | `access-control-auditor`, `access-control-auditor`, `access-control-auditor`, `accessibility`, `accessibility-test-scanner`, `accessibility` |
| `configure-ecc` | `skill`, `everything-claude-code`, `python-patterns`, `eval-harness`, `quarkus-tdd`, `java-coding-standards` |
| `mle-workflow` | `eval-harness`, `api-design`, `documentation-lookup`, `token-budget-advisor`, `canary-watch`, `code-tour` |
| `prompt-optimizer` | `everything-claude-code`, `skill`, `code-review`, `blueprint`, `search-first`, `quarkus-tdd` |
| `marketing-ops` | `marketing-context`, `seo-audit`, `skill`, `launch-strategy`, `signup-flow-cro`, `ad-creative` |
| `writing-skills` | `freeze`, `skill`, `test-driven-development`, `template`, `search`, `verification-before-completion` |
| `marketing-skills` | `marketing-ops`, `skill`, `marketing-context`, `marketing-demand-acquisition`, `marketing-strategy-pmm`, `brand-guidelines` |
| `chief-of-staff` | `agent-protocol`, `skill`, `context-engine`, `change-management`, `org-health-diagnostic`, `decision-logger` |
| `engineering-advanced-skills` | `agent-designer`, `skill`, `graphql`, `feature-flags-architect`, `api-design`, `api-test-suite-builder` |
| `chief-ai-officer-advisor` | `rag-architect`, `agent-designer`, `prompt-governance`, `self-eval`, `llm-cost-optimizer`, `deployment` |
| `c-level-skills` | `agent-protocol`, `skill`, `chief-of-staff`, `c-level-agents`, `executive-mentor`, `context-engine` |
| `autonomous-loops` | `merge`, `review`, `verification-loop`, `environment`, `skill`, `security-review` |
| `subagent-driven-development` | `finishing-a-development-branch`, `test-driven-development`, `code-review`, `code-reviewer`, `executing-plans`, `writing-plans` |
| `chief-data-officer-advisor` | `database-designer`, `observability-designer`, `data-quality-auditor`, `sql-database-assistant`, `rag-architect`, `llm-cost-optimizer` |
| `continuous-learning-v2` | `projects`, `promote`, `continuous-learning`, `skill-creator`, `status`, `continuous-learning` |
| `strategic-compact` | `memory`, `status`, `continuous-learning`, `memory`, `status`, `security-review` |
| `vpe-advisor` | `slo-architect`, `cto-advisor`, `chro-advisor`, `coo-advisor`, `chaos-engineering`, `feature-flags-architect` |
| `agent-sdk-master` | `eval`, `search`, `template`, `deploy`, `gemini`, `templates` |
| `agent-sort` | `frontend-patterns`, `django-patterns`, `skill`, `skill-stocktake`, `configure-ecc`, `strategic-compact` |
| `ecc-tools-cost-audit` | `agentic-engineering`, `customer-billing-ops`, `everything-claude-code`, `security-review`, `verification-loop`, `search-first` |
| `senior-backend` | `database`, `api-design-reviewer`, `database-designer`, `migration-architect`, `slo-architect`, `observability-designer` |
| `senior-security` | `security-pen-testing`, `incident-response`, `incident-commander`, `senior-secops`, `adversarial-reviewer`, `code-reviewer` |
| `senior-prompt-engineer` | `run`, `senior-ml-engineer`, `eval`, `rag-architect`, `agent-designer`, `ml-engineer` |
| `skill-creator` | `generate`, `benchmark`, `eval`, `skill`, `example-skill`, `generate` |
| `design-system` | `onboard`, `landing`, `brand`, `clinical-research`, `design`, `grill-with-docs` |
| `programmatic-seo` | `service`, `templates`, `resume`, `schema-markup`, `site-architecture`, `content-strategy` |
| `senior-fullstack` | `projects`, `architecture`, `api-design-reviewer`, `database-designer`, `slo-architect`, `ci-cd-pipeline-builder` |
| `ceo-advisor` | `board`, `agent-protocol`, `skill`, `stress-test`, `culture-architect`, `board-prep` |
| `compliance-readiness` | `compliance-os`, `skill`, `iso42001-specialist`, `eu-ai-act-specialist`, `information-security-manager-iso27001`, `soc2-compliance` |
| `copywriting` | `email-sequence`, `marketing-ideas`, `content-humanizer`, `copy-editing`, `content-strategy`, `marketing-context` |

---

## Intra-repo wiring clusters

Top 12 clusters of mutually referencing skills within a single repo.
Full membership for every cluster is in [`data/skill_clusters.json`](../data/skill_clusters.json) —
large clusters are truncated below so one repo's skill list doesn't dominate the page.

| Size | Skills |
|---|---|
| 1229 | `3d-web-experience`, `a11y-audit`, `ab-test-setup`, `access-control-auditor`, `accessibility`, `accessibility-test-scanner`, `account-executive`, `activation-funnel`, `active-directory-attacks`, `ad-creative`, `adversarial-reviewer`, `aeo`, `aeon`, `agent-architecture-audit`, `agent-designer`, *+1214 more* |
| 11 | `2d-games`, `3d-games`, `game-art`, `game-audio`, `game-design`, `game-development`, `mobile-games`, `multiplayer`, `pc-games`, `vr-ar`, `web-games` |
| 3 | `csharp-testing`, `dotnet-patterns`, `fsharp-testing` |
| 3 | `docs-search`, `graph-query`, `memory-search` |
| 3 | `artifacts-builder`, `shadcn`, `web-artifacts-builder` |
| 3 | `difficult-workplace-conversations`, `feedback-mastery`, `professional-communication` |
| 3 | `gitlab-skill`, `hatchling`, `pypi-readme-creator` |
| 2 | `pw`, `testrail` |
| 2 | `gateguard`, `safety-guard` |
| 2 | `remotion`, `remotion-best-practices` |
| 2 | `astropy`, `memory` |
| 2 | `gh-actions-validator`, `vertex-engine-inspector` |

---

## Cross-repo wiring (sample)

Skills in one repository explicitly referencing skills defined in another — the clearest
signal of emergent ecosystem-level integration.

| Source repo | Source skill | → Target skill | Target repo(s) | Signal |
|---|---|---|---|---|
| `anthropics/skills` | `canvas-design` | `design` | `nextlevelbuilder/ui-ux-pro-max-skill, nextlevelbuilder/ui-ux-pro-max-skill` | sequential_cue |
| `anthropics/skills` | `claude-api` | `extract` | `alirezarezvani/claude-skills` | slash_command |
| `anthropics/skills` | `claude-api` | `gemini` | `davila7/claude-code-templates` | slash_command |
| `anthropics/skills` | `claude-api` | `prompt-caching` | `davila7/claude-code-templates` | slash_command |
| `anthropics/skills` | `doc-coauthoring` | `projects` | `davila7/claude-code-templates` | slash_command |
| `anthropics/skills` | `frontend-design` | `brief` | `alirezarezvani/claude-skills` | sequential_cue |
| `anthropics/skills` | `pptx` | `templates` | `davila7/claude-code-templates, davila7/claude-code-templates` | sequential_cue |
| `anthropics/skills` | `skill-creator` | `generate` | `alirezarezvani/claude-skills` | slash_command |
| `anthropics/skills` | `skill-creator` | `benchmark` | `affaan-m/ECC, affaan-m/ECC` | slash_command |
| `anthropics/skills` | `skill-creator` | `eval` | `alirezarezvani/claude-skills` | slash_command |
| `anthropics/skills` | `skill-creator` | `skill` | `BbgnsurfTech/claude-skills-collection` | sequential_cue |
| `anthropics/skills` | `web-artifacts-builder` | `shadcn` | `davila7/claude-code-templates` | sequential_cue |
| `alirezarezvani/claude-skills` | `business-growth-skills` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `contract-and-proposal-writer` | `docx` | `anthropics/skills, davila7/claude-code-templates` | sequential_cue |
| `alirezarezvani/claude-skills` | `vendor-management` | `fintech` | `borghei/claude-skills` | slash_command |
| `alirezarezvani/claude-skills` | `boardroom` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `brief` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `caio-review` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `cco-review` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `cdo-review` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `cfo-review` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `ciso-review` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `cmo-review` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `cpo-review` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `cro-review` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `cross-eval` | `codex` | `davila7/claude-code-templates` | slash_command |
| `alirezarezvani/claude-skills` | `cross-eval` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `cto-review` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `decide` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |
| `alirezarezvani/claude-skills` | `execute` | `skill` | `BbgnsurfTech/claude-skills-collection` | slash_command |

---

## What this implies

The corpus already contains an implicit wiring layer — skills reference each other by
slash-command syntax and sequential language, forming chains and clusters that no
published standard captures. The patterns fall into three types:

**1. Sequential pipelines** — skill A says "after running /skill-B"; ordering is
   declared unilaterally by one skill, invisible to the other.

**2. Coordinator skills** — one skill orchestrates several others by naming them
   explicitly; the sub-skills have no awareness of the coordinator.

**3. Ecosystem hubs** — a small number of skills (see most-referenced table) are
   referenced widely across unrelated repos, suggesting emergent standards.

None of these wirings are machine-readable. A consumer of the corpus has no way to
discover that skill A depends on skill B except by reading prose. This is the gap
a `wiring.md` convention would close.

---

*Generated by `crawlers/discover_wiring.py`. Re-run to refresh.*
