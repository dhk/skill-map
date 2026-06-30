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
| `configure-ecc` | `skill`, `everything-claude-code`, `python-patterns`, `springboot-tdd`, `tdd-workflow`, `strategic-compact` |
| `mle-workflow` | `git-workflow`, `tdd-workflow`, `strategic-compact`, `database-migrations`, `architecture-decision-records`, `opensource-pipeline` |
| `prompt-optimizer` | `everything-claude-code`, `skill`, `code-review`, `blueprint`, `search-first`, `compose-multiplatform-patterns` |
| `marketing-ops` | `marketing-context`, `seo-audit`, `skill`, `webinar-marketing`, `free-tool-strategy`, `site-architecture` |
| `writing-skills` | `freeze`, `skill`, `test-driven-development`, `template`, `search`, `verification-before-completion` |
| `marketing-skills` | `marketing-ops`, `skill`, `marketing-context`, `marketing-demand-acquisition`, `marketing-strategy-pmm`, `brand-guidelines` |
| `chief-of-staff` | `agent-protocol`, `skill`, `competitive-intel`, `company-os`, `intl-expansion`, `change-management` |
| `engineering-advanced-skills` | `agent-designer`, `skill`, `graphql`, `secrets-vault-manager`, `interview-system-designer`, `feature-flags-architect` |
| `chief-ai-officer-advisor` | `rag-architect`, `agent-designer`, `prompt-governance`, `self-eval`, `llm-cost-optimizer`, `deployment` |
| `c-level-skills` | `agent-protocol`, `skill`, `chief-of-staff`, `c-level-agents`, `executive-mentor`, `competitive-intel` |
| `autonomous-loops` | `merge`, `review`, `verification-loop`, `environment`, `skill`, `tdd-workflow` |
| `subagent-driven-development` | `requesting-code-review`, `test-driven-development`, `finishing-a-development-branch`, `executing-plans`, `code-review`, `writing-plans` |
| `chief-data-officer-advisor` | `database-designer`, `observability-designer`, `data-quality-auditor`, `sql-database-assistant`, `rag-architect`, `llm-cost-optimizer` |
| `continuous-learning-v2` | `projects`, `promote`, `continuous-learning`, `skill-creator`, `status`, `continuous-learning` |
| `strategic-compact` | `memory`, `status`, `continuous-learning`, `memory`, `status`, `tdd-workflow` |
| `vpe-advisor` | `slo-architect`, `cto-advisor`, `chro-advisor`, `coo-advisor`, `chaos-engineering`, `feature-flags-architect` |
| `agent-sdk-master` | `eval`, `search`, `template`, `deploy`, `gemini`, `templates` |
| `agent-sort` | `frontend-patterns`, `django-patterns`, `skill`, `strategic-compact`, `configure-ecc`, `skill-stocktake` |
| `ecc-tools-cost-audit` | `tdd-workflow`, `agentic-engineering`, `autonomous-loops`, `security-review`, `search-first`, `everything-claude-code` |
| `senior-backend` | `database`, `api-design-reviewer`, `database-designer`, `migration-architect`, `slo-architect`, `observability-designer` |
| `senior-security` | `security-pen-testing`, `incident-response`, `incident-commander`, `senior-secops`, `adversarial-reviewer`, `code-reviewer` |
| `senior-prompt-engineer` | `run`, `senior-ml-engineer`, `eval`, `rag-architect`, `agent-designer`, `ml-engineer` |
| `skill-creator` | `generate`, `benchmark`, `eval`, `skill`, `example-skill`, `generate` |
| `design-system` | `onboard`, `landing`, `brand`, `clinical-research`, `design`, `research-ops` |
| `programmatic-seo` | `service`, `templates`, `resume`, `site-architecture`, `marketing-context`, `seo-audit` |
| `senior-fullstack` | `projects`, `architecture`, `api-design-reviewer`, `database-designer`, `slo-architect`, `ci-cd-pipeline-builder` |
| `ceo-advisor` | `board`, `agent-protocol`, `skill`, `board-prep`, `culture-architect`, `stress-test` |
| `compliance-readiness` | `compliance-os`, `skill`, `iso42001-specialist`, `eu-ai-act-specialist`, `information-security-manager-iso27001`, `soc2-compliance` |
| `copywriting` | `marketing-context`, `copy-editing`, `content-humanizer`, `ab-test-setup`, `email-sequence`, `social-content` |

---

## Intra-repo wiring clusters

Top 12 clusters of mutually referencing skills within a single repo.

| Size | Skills |
|---|---|
| 1229 | `3d-web-experience`, `a11y-audit`, `ab-test-setup`, `access-control-auditor`, `accessibility`, `accessibility-test-scanner`, `account-executive`, `activation-funnel`, `active-directory-attacks`, `ad-creative`, `adversarial-reviewer`, `aeo`, `aeon`, `agent-architecture-audit`, `agent-designer`, `agent-development`, `agent-eval`, `agent-evaluation`, `agent-factory`, `agent-harness-construction`, `agent-introspection-debugging`, `agent-management`, `agent-md-refactor`, `agent-memory-systems`, `agent-orchestration`, `agent-payment-x402`, `agent-protocol`, `agent-sdk-master`, `agent-self-evaluation`, `agent-sort`, `agent-tool-builder`, `agent-workflow-designer`, `agenthub`, `agentic-engineering`, `agents-crewai`, `agents-langchain`, `agile-coach`, `agile-product-owner`, `agirails-agent-payments`, `ai-act-readiness`, `ai-agents-architect`, `ai-ethics-validator`, `ai-feature-prd`, `ai-regression-testing`, `ai-security`, `ai-seo`, `ai-wrapper-product`, `aims-audit`, `alphafold-database`, `analytics-engineer`, `analytics-tracking`, `android-cicd`, `android-clean-architecture`, `angular`, `angular-developer`, `anndata`, `anomaly-detection-system`, `ansible-playbook-creator`, `ansoff-matrix`, `api-connector-builder`, `api-design`, `api-design-reviewer`, `api-documentation-generator`, `api-fuzzing-bug-bounty`, `api-patterns`, `api-security-best-practices`, `api-security-testing`, `api-test-suite-builder`, `app-builder`, `app-store-optimization`, `apple-hig-expert`, `application-profiler`, `arboreto`, `architecture`, `architecture-decision-records`, `architecture-patterns`, `article-writing`, `astro`, `atlassian-admin`, `atlassian-templates`, `authentication-validator`, `automation-audit-ops`, `automl-pipeline-builder`, `autonomous-agent-harness`, `autonomous-agent-patterns`, `autonomous-agents`, `autonomous-loops`, `autoresearch-agent`, `aws-penetration-testing`, `aws-serverless`, `aws-solution-architect`, `azure-cloud-architect`, `azure-functions`, `backend-architect`, `backend-dev-guidelines`, `backend-patterns`, `backlog-refinement`, `banner-design`, `bash-linux`, `bash-pro`, `behavioral-modes`, `behuman`, `benchling-integration`, `benchmark`, `benchmark-methodology`, `best-practices`, `beta-program`, `biopython`, `bioservices`, `bleu`, `blockrun`, `blueprint`, `board`, `board-deck-builder`, `board-meeting`, `board-prep`, `boardroom`, `brainstorm-experiments`, `brainstorm-ideas`, `brainstorm-okrs`, `brainstorming`, `brand`, `brand-discovery`, `brand-guidelines`, `brand-strategist`, `brand-voice`, `brief`, `bright-data-best-practices`, `bright-data-mcp`, `brightdata-local-search`, `broken-authentication`, `browser-automation`, `browser-extension-builder`, `browser-qa`, `bullmq-specialist`, `bun-runtime`, `burp-suite-testing`, `business-growth-skills`, `business-intelligence`, `business-investment-advisor`, `business-model-canvas`, `business-operations-skills`, `c-level-agents`, `c-level-skills`, `c4-architecture`, `caio-review`, `calendar-prep`, `campaign-analytics`, `canary-watch`, `canvas-design`, `capa-officer`, `capacity-planner`, `capture`, `career-changer-translator`, `carrier-relationship-management`, `cc-skill-project-guidelines-example`, `cc-skill-security-review`, `cco-review`, `ccpa-cpra-privacy-expert`, `cdo-review`, `cellxgene-census`, `ceo-advisor`, `cf-crawl`, `cfo-advisor`, `cfo-review`, `challenge`, `change-management`, `changelog-generator`, `channel-economics`, `chaos-engineering`, `chief-ai-officer-advisor`, `chief-customer-officer-advisor`, `chief-data-officer-advisor`, `chief-of-staff`, `chro-advisor`, `chrome-extension-developer`, `churn-prevention`, `ci-cd-pipeline-builder`, `cisco-ios-patterns`, `ciso-advisor`, `ciso-review`, `citation-management`, `clang-format`, `classification-model-builder`, `claude-api`, `claude-code-mastery`, `claude-code-sessions`, `claude-d3js-skill`, `clean-code`, `clickhouse-io`, `climate-tech`, `clinical-decision-support`, `clinical-reports`, `clinical-research`, `clinpgx-database`, `clinvar-database`, `cloud-architect`, `cloud-devops`, `cloud-penetration-testing`, `cloud-run-basics`, `cloud-security`, `cloudflare-deploy`, `clustering-algorithm-runner`, `cmo-advisor`, `cmo-review`, `cobrapy`, `cocoindex`, `code-formatter`, `code-review`, `code-review-checklist`, `code-reviewer`, `code-to-prd`, `code-tour`, `codebase-onboarding`, `codehealth-mcp`, `codex`, `codex-cli-bridge`, `codex-cli-specialist`, `codex-review`, `coding-standards`, `cold-email`, `collision-zone-thinking`, `command-creator`, `command-development`, `commercial-forecaster`, `commercial-policy`, `commercial-skills`, `commit`, `commit-smart`, `commitlint`, `company-os`, `competitive-ads-extractor`, `competitive-intel`, `competitive-platform-analysis`, `competitive-report-structure`, `competitive-teardown`, `competitor-alternatives`, `compliance-checker`, `compliance-os`, `compliance-readiness`, `compliance-report-generator`, `compose-multiplatform-patterns`, `computer-use-agents`, `computer-vision-processor`, `concise-planning`, `condition-based-waiting`, `config-gc`, `configure-ecc`, `confluence-expert`, `connections-optimizer`, `content-creator`, `content-engine`, `content-humanizer`, `content-production`, `content-strategy`, `context-budget`, `context-engine`, `context-window-management`, `context7-auto-research`, `continuous-agent-loop`, `continuous-learning`, `continuous-learning-v2`, `contract-and-proposal-writer`, `contract-review`, `conventional-commits`, `conversation-memory`, `convex`, `coo-advisor`, `copy-editing`, `copywriting`, `core-components`, `core-web-vitals`, `cors-policy-validator`, `cosmic-database`, `cost-aware-llm-pipeline`, `cost-tracking`, `council`, `coverage`, `cpo-advisor`, `cpo-review`, `cpp-coding-standards`, `cpp-testing`, `cpu-usage-monitor`, `create-pr`, `create-prd`, `crewai`, `cro-advisor`, `cro-review`, `cross-eval`, `crosspost`, `cs-onboard`, `cto-advisor`, `cto-review`, `culture-architect`, `customer-billing-ops`, `customer-feedback-triage`, `customer-interview-script`, `customer-success-manager`, `customs-trade-compliance`, `cycle-time-analyzer`, `daci-framework`, `daily-meeting-update`, `dart-flutter-patterns`, `dashboard-builder`, `dask`, `data-analyst`, `data-privacy-scanner`, `data-quality-auditor`, `data-scientist`, `data-validation-engine`, `database`, `database-architect`, `database-deadlock-detector`, `database-design`, `database-designer`, `database-diff-tool`, `database-documentation-gen`, `database-index-advisor`, `database-migration`, `database-migrations`, `database-optimizer`, `database-recovery-manager`, `database-replication-manager`, `database-schema-designer`, `database-security-scanner`, `database-transaction-monitor`, `datacommons-client`, `datadog-cli`, `datamol`, `deal-desk`, `decide`, `decision-logger`, `deep-research`, `deep-research-notebooklm`, `deepchem`, `defense-in-depth`, `delivery-manager`, `demo-video`, `denario`, `dependency-auditor`, `dependency-checker`, `dependency-map`, `deploy`, `deployment`, `deployment-patterns`, `deployment-procedures`, `design`, `design-auditor`, `design-mirror`, `design-system`, `design-system-lead`, `design-system-starter`, `design-to-code`, `devops-iac-engineer`, `devops-workflow-engineer`, `diffdock`, `dispatching-parallel-agents`, `distributed-training-accelerate`, `distributed-training-deepspeed`, `distributed-training-megatron-core`, `distributed-training-pytorch-fsdp`, `distributed-training-pytorch-lightning`, `django-celery`, `django-patterns`, `django-pro`, `django-security`, `django-tdd`, `django-verification`, `dmux-workflows`, `doc`, `doc-coauthoring`, `doc-drift-detector`, `docker-compose-generator`, `docker-development`, `docker-expert`, `docker-patterns`, `documentation-lookup`, `documentation-templates`, `docx`, `docx-toolkit`, `domain`, `domain-driven-design`, `domain-name-brainstormer`, `dora-compliance-expert`, `dossier`, `dotnet-backend`, `dpia-assessment`, `drizzle-orm-expert`, `drugbank-database`, `e2e-testing`, `ecc-guide`, `ecc-tools-cost-audit`, `edtech`, `electron-development`, `email-ops`, `email-sequence`, `email-systems`, `email-template-builder`, `emerging-techniques-long-context`, `ena-database`, `encryption-tool`, `energy-procurement`, `engineering-advanced-skills`, `engineering-skills`, `env-secrets-manager`, `environment`, `environment-config-manager`, `environment-setup-guide`, `eol-communication`, `epic-design`, `error-handling`, `esm`, `etetoolkit`, `ethical-hacking-methodology`, `eu-ai-act-specialist`, `eval`, `eval-harness`, `event-sourcing-architect`, `everything-claude-code`, `exa-search`, `excalidraw`, `execute`, `executing-marketing-campaigns`, `executing-plans`, `executive-mentor`, `executive-resume-writer`, `experiment-designer`, `extract`, `fal-ai-media`, `fastapi-endpoint`, `fastapi-patterns`, `fastmcp-creator`, `fda-consultant-specialist`, `fda-qsr-audit-prep`, `feature-design-assistant`, `feature-engineering-toolkit`, `feature-flag-strategy`, `feature-flags-architect`, `figma`, `figma-implement-design`, `file-organizer`, `file-path-traversal`, `finance-billing-ops`, `finance-skills`, `financial-analyst`, `fine-tuning-peft`, `finishing-a-development-branch`, `fintech`, `firebase`, `firebase-basics`, `firecrawl-scraper`, `fix`, `flutter-dart-code-review`, `flutter-expert`, `focused-fix`, `form-cro`, `founder-coach`, `founder-mode`, `free-tool-strategy`, `freeze`, `frontend-a11y`, `frontend-design`, `frontend-design-direction`, `frontend-dev-guidelines`, `frontend-patterns`, `frontend-slides`, `full-page-screenshot`, `gardening-skills-wiki`, `gc-review`, `gcp-cloud-architect`, `gcp-cloud-run`, `gdpr-audit-prep`, `gdpr-compliance-scanner`, `gdpr-dsgvo-expert`, `gemini`, `gemini-api-agent-platform`, `general-counsel-advisor`, `generate`, `generate-image`, `geniml`, `geo-database`, `geo-fundamentals`, `geopandas`, `get-available-resources`, `gget`, `git-commit-helper`, `git-pushing`, `git-workflow`, `git-worktree-manager`, `github-actions-templates`, `github-ops`, `github-workflow-automation`, `gitops-workflow`, `golang-patterns`, `golang-pro`, `golang-testing`, `google-analytics`, `google-cloud-auth`, `google-cloud-onboarding`, `google-cloud-waf-cost-optimization`, `google-cloud-waf-reliability`, `google-cloud-waf-security`, `google-workspace-cli`, `grafana-dashboards`, `grants`, `graphql`, `graphql-architect`, `grill-me`, `grill-with-docs`, `growth-marketer`, `gtars`, `gtm-strategy`, `gwas-database`, `handoff`, `hard-call`, `healthcare-emr-patterns`, `healthcare-eval-harness`, `healthcare-phi-compliance`, `healthtech`, `helm-chart-builder`, `helm-chart-generator`, `helm-chart-scaffolding`, `heygen-best-practices`, `hipaa-compliance`, `hipaa-compliance-checker`, `hmdb-database`, `holistic-linting`, `homelab-network-readiness`, `homelab-network-setup`, `homelab-pihole-dns`, `homelab-vlan-segmentation`, `homelab-wireguard-vpn`, `hono`, `hook-development`, `hook-factory`, `hr-business-partner`, `html-injection-testing`, `hyperparameter-tuner`, `hypogenic`, `hypothesis-generation`, `i18n-localization`, `ideal-customer-profile`, `identify-assumptions`, `idor-testing`, `inbox-setup`, `inbox-triage`, `incident-commander`, `incident-responder`, `incident-response`, `inference-serving-sglang`, `inference-serving-vllm`, `information-security-manager-iso27001`, `infrastructure-as-code-generator`, `infrastructure-compliance-auditor`, `infrastructure-modal`, `init`, `inngest`, `input-validation-scanner`, `intent-driven-development`, `interactive-portfolio`, `internal-comms`, `internal-narrative`, `interview-prep-generator`, `interview-synthesis`, `interview-system-designer`, `intl-expansion`, `inventory-demand-planning`, `inversion-exercise`, `investor-materials`, `investor-outreach`, `invoice-organizer`, `isms-audit-expert`, `iso13485-audit-prep`, `iso27001-audit-prep`, `iso42001-ai-management`, `iso42001-specialist`, `iterative-retrieval`, `ito-basket-compare`, `ito-data-atlas-agent`, `ito-market-intelligence`, `ito-trade-planner`, `java-coding-standards`, `jira`, `jira-automation`, `jira-expert`, `job-description-analyzer`, `job-stories`, `jpa-patterns`, `jtbd-workshop`, `jupyter-notebook`, `k6-load-testing`, `karpathy-coder`, `kegg-database`, `knowledge-ops`, `kotlin-coroutines-flows`, `kotlin-testing`, `kubernetes-architect`, `kubernetes-operator`, `kubernetes-patterns`, `lamindb`, `landing`, `landing-page-generator`, `langfuse`, `langgraph`, `laravel-patterns`, `laravel-plugin-discovery`, `laravel-security`, `laravel-tdd`, `laravel-verification`, `latex-posters`, `launch-playbook`, `launch-strategy`, `lead-intelligence`, `lead-research-assistant`, `lead-researcher`, `lean-canvas`, `linear`, `linear-automation`, `linear-expert`, `lint-and-validate`, `linux-privilege-escalation`, `liquid-glass-design`, `litellm`, `literature-review`, `litreview`, `llamafile`, `llm-cost-optimizer`, `llm-evaluation`, `llm-trading-agent-security`, `llm-wiki`, `load-balancer-tester`, `logistics-exception-management`, `loki-mode`, `loop`, `ma-playbook`, `make-interfaces-feel-better`, `manifest`, `manim-video`, `markdown-html-orchestrator`, `market-research`, `market-research-reports`, `marketing-analyst`, `marketing-campaign`, `marketing-context`, `marketing-demand-acquisition`, `marketing-ideas`, `marketing-ops`, `marketing-psychology`, `marketing-skills`, `marketing-strategy-pmm`, `marketplace`, `markitdown`, `marp-slide`, `matplotlib`, `mcp-builder`, `mcp-integration`, `mcp-server-builder`, `mcp-server-patterns`, `md-document`, `md-review`, `md-slides`, `mdr-745-specialist`, `medchem`, `meeting-analyzer`, `meeting-insights`, `meme-factory`, `merge`, `mermaid-diagram-specialist`, `messages-ops`, `meta-pattern-recognition`, `metasploit-framework`, `metrics`, `metrics-dashboard`, `micro-saas-launcher`, `migration-architect`, `ml-adoption-playbook`, `ml-engineer`, `ml-ops-engineer`, `ml-paper-writing`, `mle-workflow`, `mlops-mlflow`, `mobile-design`, `modal`, `model-architecture-mamba`, `model-architecture-nanogpt`, `model-architecture-rwkv`, `model-evaluation-suite`, `model-versioning-tracker`, `molfeat`, `monorepo-navigator`, `motion-advanced`, `motion-canvas`, `motion-foundations`, `motion-patterns`, `motion-ui`, `ms365-tenant-manager`, `mui`, `mysql-patterns`, `n8n-mcp-tools-expert`, `n8n-workflow-patterns`, `nanoclaw-repl`, `nda-review`, `nda-triage`, `neon-instagres`, `nestjs-expert`, `nestjs-patterns`, `netmiko-ssh-automation`, `network-101`, `network-bgp-diagnostics`, `network-config-validation`, `network-interface-health`, `network-policy-manager`, `networkx`, `neural-network-builder`, `neuropixels-analysis`, `new`, `nextjs-app-router-patterns`, `nextjs-best-practices`, `nextjs-supabase-auth`, `nextjs-turbopack`, `nis2-directive-specialist`, `nist-csf-specialist`, `nlp-text-analyzer`, `nodejs-backend-patterns`, `nodejs-best-practices`, `north-star-metric`, `notebooklm`, `notion-knowledge-capture`, `notion-meeting-intelligence`, `notion-pm`, `notion-research-documentation`, `notion-spec-to-implementation`, `notion-template-business`, `observability-designer`, `observability-engineer`, `observability-phoenix`, `obsidian-clipper-template-creator`, `office-hours`, `onboard`, `onboarding-cro`, `openalex-database`, `openclaw-persona-forge`, `opensource-pipeline`, `opentargets-database`, `opentrons-integration`, `opportunity-solution-tree`, `optimization-bitsandbytes`, `optimization-gguf`, `optimization-gptq`, `orch-add-feature`, `orch-build-mvp`, `orch-change-feature`, `orch-fix-defect`, `orch-pipeline`, `orch-refine-code`, `org-health-diagnostic`, `outcome-roadmap`, `overnight-dev`, `owasp-compliance-checker`, `page-cro`, `paid-ads`, `paper-2-web`, `parallel-agents`, `partnerships-architect`, `patent`, `pathml`, `paywall-upgrade-cro`, `pb-sdk`, `pci-dss-specialist`, `pci-dss-validator`, `pdb-database`, `pdf`, `pdf-anthropic`, `pdf-official`, `pdf-processing`, `pdf-toolkit`, `peer-review`, `penetration-tester`, `pennylane`, `pentest-checklist`, `pentest-commands`, `people-analytics`, `performance`, `performance-optimizer`, `performance-profiler`, `performance-profiling`, `performance-test-suite`, `perl-patterns`, `perl-security`, `perl-testing`, `perplexity`, `perplexity-search`, `personal-tool-builder`, `pi-pathfinder`, `pitch-deck-reviewer`, `plan-orchestrate`, `plankton-code-quality`, `planning`, `planning-with-files`, `playwright`, `playwright-e2e-builder`, `playwright-pro`, `playwright-skill`, `plotly`, `plugin-forge`, `plugin-settings`, `plugin-structure`, `plugin-validator`, `pm-1on1s`, `pm-career-ladder`, `pm-interview-prep`, `pm-onboarding`, `pm-skills`, `polars`, `popup-cro`, `porters-five-forces`, `portfolio-case-study-writer`, `post-mortem`, `post-training-grpo-rl-training`, `post-training-slime`, `postgres-best-practices`, `postgres-patterns`, `postgres-schema-design`, `postgresql`, `postgresql-optimization`, `postmortem`, `pptx`, `pptx-official`, `pptx-posters`, `pptx-toolkit`, `pr-review-expert`, `pre-commit`, `pre-mortem`, `prediction-market-oracle-research`, `prediction-market-risk-review`, `preserving-productive-tensions`, `prfaq`, `pricing-prd`, `pricing-strategist`, `pricing-strategy`, `prioritization-frameworks`, `prisma-expert`, `prisma-patterns`, `privacy-compliance`, `privacy-notice-generator`, `privilege-escalation-methods`, `process-mapper`, `procurement-optimizer`, `product-analytics`, `product-capability`, `product-designer`, `product-discovery`, `product-lens`, `product-manager-toolkit`, `product-research`, `product-skills`, `product-strategist`, `product-vision`, `productboard-expert`, `production-audit`, `production-code-audit`, `production-scheduling`, `program-manager`, `programmatic-seo`, `progressive-web-app`, `project-flow-ops`, `project-guidelines-example`, `projects`, `prometheus-configuration`, `prompt-caching`, `prompt-engineer`, `prompt-engineer-toolkit`, `prompt-governance`, `prompt-optimization-claude-45`, `prompt-optimizer`, `pubmed-database`, `pufferlib`, `pulling-updates-from-skills-repository`, `pulse`, `pydantic-ai`, `pydeseq2`, `pyhealth`, `pymc`, `pyopenms`, `python-patterns`, `python-pro`, `python-testing`, `python3-development`, `pytorch-lightning`, `pytorch-patterns`, `qa-browser-automation`, `qa-test-planner`, `qms-audit-expert`, `quality-documentation-manager`, `quality-manager-qmr`, `quality-manager-qms-iso13485`, `quality-nonconformance`, `quarkus-patterns`, `quarkus-security`, `quarkus-tdd`, `quarkus-verification`, `quarterly-planning`, `query-performance-analyzer`, `ra-qm-skills`, `rag-architect`, `rag-engineer`, `rag-implementation`, `rag-qdrant`, `rag-sentence-transformers`, `railway-docs`, `ralphinho-rfc-pipeline`, `rdkit`, `react-best-practices`, `react-native-architecture`, `react-patterns`, `react-performance`, `react-testing`, `react-ui-patterns`, `reactome-database`, `receiving-code-review`, `recommendation-engine`, `red-team`, `red-team-tools`, `redis-patterns`, `referral-program`, `reflect`, `regression-analysis-tool`, `regulatory-affairs-head`, `release-manager`, `release-notes`, `release-orchestrator`, `remembering-conversations`, `remotion-video-creation`, `render-deploy`, `repo-scan`, `report`, `requesting-code-review`, `research`, `research-finance`, `research-grants`, `research-lookup`, `research-ops`, `research-ops-skills`, `research-summarizer`, `resource-usage-tracker`, `response-time-tracker`, `resume`, `resume-ats-optimizer`, `resume-bullet-writer`, `resume-formatter`, `resume-quantifier`, `resume-tailor`, `resume-version-manager`, `returns-reverse-logistics`, `revenue-operations`, `review`, `rfp-responder`, `risk-management-specialist`, `roadmap-communication`, `roadmap-communicator`, `roier-seo`, `root-cause-tracing`, `rules-distill`, `run`, `runbook-generator`, `rust-testing`, `saas-metrics-coach`, `saas-multi-tenant`, `saas-scaffolder`, `safety-alignment-llamaguard`, `safety-alignment-nemo-guardrails`, `sales-engineer`, `sales-operations`, `santa-method`, `sast-configuration`, `scale-game`, `scanning-tools`, `scanpy`, `scenario-war-room`, `schema-markup`, `scholar-evaluation`, `scientific-brainstorming`, `scientific-critical-thinking`, `scientific-db-uspto-database`, `scientific-schematics`, `scientific-slides`, `scientific-visualization`, `scientific-writing`, `scikit-bio`, `scikit-learn`, `scikit-survival`, `scrape`, `screenshot`, `scroll-experience`, `scrum-master`, `scrum-master-agent`, `scvi-tools`, `seaborn`, `search`, `search-first`, `secret-scanner`, `secrets-management`, `secrets-vault-manager`, `security-agent`, `security-audit`, `security-best-practices`, `security-compliance`, `security-guidance`, `security-misconfiguration-finder`, `security-pen-testing`, `security-pro-pack`, `security-review`, `security-scan`, `security-test-scanner`, `security-threat-model`, `self-eval`, `self-improving-agent`, `senior-architect`, `senior-backend`, `senior-cloud-architect`, `senior-computer-vision`, `senior-data-engineer`, `senior-data-scientist`, `senior-devops`, `senior-frontend`, `senior-fullstack`, `senior-ml-engineer`, `senior-mobile`, `senior-pm`, `senior-prompt-engineer`, `senior-qa`, `senior-secops`, `senior-security`, `seo`, `seo-audit`, `seo-fundamentals`, `seo-optimizer`, `seo-specialist`, `service`, `setup`, `shap`, `sharing-skills`, `ship-gate`, `ship-learn-next`, `shodan-reconnaissance`, `shopify-apps`, `shopify-development`, `signup-flow-cro`, `simplification-cascades`, `site-architecture`, `skill`, `skill-adapter`, `skill-comply`, `skill-creation-guide`, `skill-creator`, `skill-developer`, `skill-development`, `skill-judge`, `skill-scout`, `skill-security-auditor`, `skill-share`, `skill-stocktake`, `skill-tester`, `slack-automation`, `slides`, `slo-architect`, `smtp-penetration-testing`, `snowflake-development`, `soc2-audit-helper`, `soc2-audit-prep`, `soc2-compliance`, `soc2-compliance-expert`, `social-content`, `social-graph-ranker`, `social-media-analyzer`, `social-media-manager`, `social-publisher`, `solutions-architect`, `spawn`, `spec-driven-workflow`, `spec-to-repo`, `speech`, `springboot-patterns`, `springboot-security`, `springboot-tdd`, `springboot-verification`, `sprint-plan`, `sprint-retrospective`, `sql-database-assistant`, `sql-injection-detector`, `sql-injection-testing`, `sql-pro`, `sql-query-optimizer`, `sqlmap-database-pentesting`, `ssl-certificate-manager`, `stakeholder-map`, `statistical-analyst`, `statsmodels`, `status`, `status-update-generator`, `stored-procedure-generator`, `story-mapping`, `story-splitting`, `strategic-alignment`, `strategic-compact`, `stress-test`, `stripe-integration`, `stripe-integration-expert`, `subagent-driven-development`, `summarize-meeting`, `supply-chain-guard`, `sveltekit`, `swarmvault`, `swift-actor-persistence`, `swift-concurrency-6-2`, `swift-protocol-di-testing`, `swiftui-patterns`, `swot-analysis`, `syllabus`, `sympy`, `systematic-debugging`, `tailwind-patterns`, `talent-acquisition`, `taste`, `tavily-web`, `tc-tracker`, `tdd-guide`, `tdd-workflow`, `team-builder`, `team-communications`, `tech-contract-negotiation`, `tech-debt-tracker`, `tech-stack-evaluator`, `telegram-bot-builder`, `telegram-mini-app`, `template`, `templates`, `terminal-ops`, `terraform-module-builder`, `terraform-patterns`, `terraform-specialist`, `test-data-generator`, `test-driven-development`, `test-orchestrator`, `test-scenarios`, `testing-anti-patterns`, `testing-patterns`, `testing-skills-with-subagents`, `threat-detection`, `threat-modeling-expert`, `throughput-analyzer`, `token-budget-advisor`, `tokenization-huggingface-tokenizers`, `tokenization-sentencepiece`, `toml-python`, `top-web-vulnerabilities`, `torchdrug`, `tracing-knowledge-lineages`, `transformers`, `treatment-plans`, `trigger-dev`, `twilio-communications`, `typescript-expert`, `typescript-pro`, `ui-design-system`, `ui-styling`, `ui-ux-pro-max`, `umap-learn`, `unified-notifications-ops`, `uniprot-database`, `universal-scraping-architect`, `upstash-qstash`, `using-git-worktrees`, `using-skills`, `using-superpowers`, `uspto-database`, `uv`, `ux-researcher-designer`, `vaex`, `value-proposition-canvas`, `vendor-due-diligence`, `vendor-management`, `venue-templates`, `vercel-deploy`, `vercel-deployment`, `verification-before-completion`, `verification-gate`, `verification-loop`, `vertex-agent-builder`, `video-content-strategist`, `video-editing`, `videodb`, `viral-generator-builder`, `vite-patterns`, `voice-agents`, `vpe-advisor`, `vpe-review`, `vue-patterns`, `vulnerability-scanner`, `web-performance-optimization`, `web-quality-audit`, `web-security-testing`, `web-to-markdown`, `webapp-testing`, `webinar-marketing`, `weekly-review`, `when-stuck`, `windows-desktop-e2e`, `workflow-automation`, `workflow-builder`, `workspace-surface-audit`, `write-a-skill`, `writing-clearly-and-concisely`, `writing-plans`, `writing-skills`, `wwas`, `x-api`, `x-twitter-growth`, `x-twitter-scraper`, `xdg-base-directory`, `xlsx`, `xlsx-toolkit`, `xss-html-injection`, `youtube-full`, `zapier-make-patterns`, `zapier-workflows`, `zarr-python`, `zinc-database`, `zod-validation-expert` |
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
