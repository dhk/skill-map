# Skill Concepts Atlas: study plan

Date: 2026-11-26 · Status: phase 1 in progress

## Question

How are the purposes and concepts in published Claude and ChatGPT skills
spreading and changing over time, and in what settings, such as industry,
language and type of repo? How sophisticated are those skills, and is that
rising?

The work comes in two parts, in this order:

1. **Exposition:** a citable catalogue that establishes the corpus, labels each
   skill's purpose, context and sophistication, and sets up later search tools.
2. **Timeline:** growth curves, concept spread and morphing. Every first-seen
   date is published as an **estimate**, with its evidence and a confidence
   level.

## Why build on prior work instead of re-crawling

File-level collection has been done at scale since the June Skill Map crawl.
What is missing is the concept and sophistication layer. The study builds that
layer on these sources:

| Source | Scale | Gives us | Does not give us |
|---|---|---|---|
| [GitSkills](https://arxiv.org/html/2608.10906) ([Zenodo](https://doi.org/10.5281/zenodo.21875637), [Hugging Face](https://huggingface.co/datasets/mvaccargiu/gitskills)) | 3,797,117 files, 282,200 repos, July 2026 | Occurrence table, content hashes, repo metadata, first/last commit dates for 458,548 records | Metadata is CC BY 4.0 but file text stays under origin licenses; exact-byte dedup only; no purpose, concept or context labels |
| [Skill Constellations](https://arxiv.org/html/2610.11169) | 2,193,119 dated adoptions | Directed copy network | Lineage of files, not ideas |
| [How Agent Skills Evolve](https://arxiv.org/html/2611.04456) | 84,200 skills | Component taxonomy and change patterns | Cross-repo spread or context |
| [From Anatomy to Smells](https://arxiv.org/html/2607.01456) | 238 coded skills | 13 high-level and 44 low-level components, 26 smells | Small sample, one marketplace |
| [Ling et al.](https://arxiv.org/pdf/2602.08004) | 40,285 skills.sh listings | Marketplace first-appearance dates | One marketplace, cross-sectional |
| [What Keeps Skills from Being Reusable?](https://arxiv.org/html/2608.08453) | 138,133 files | Defect taxonomy | Quality, not concepts |
| This repo | 4,975 skills, 43 repos, June 2026 | Quality rubric, repo signatures, lineage heuristics | Small curated corpus; "concept" here means a normalised skill name |

Source pages were read on 26 Nov 2026. GitSkills and Anatomy to Smells were
read in full; the others from abstracts and excerpts.

## Corpus

- Public GitHub `SKILL.md` files plus the major marketplaces (skills.sh,
  SkillsMP, claude-plugins.dev, ClawHub, Smithery).
- "ChatGPT skills" means public `SKILL.md` files used by ChatGPT and Codex,
  found under `.codex/skills`, `.agents/skills`, the `openai/skills` catalogue
  and OpenAI plugin repos, and recognisable by `agents/openai.yaml`.
- Custom GPTs are out of v1. AGENTS.md, CLAUDE.md, Cursor rules and Copilot
  instructions are a sibling study for later.
- Base: GitSkills, pinned to one Zenodo version, plus our own delta crawl for
  August to November 2026 and the existing Skill Map snapshots.

See [ADR 0004](../adr/0004-atlas-scope-and-corpus.md).

## Dating

Every signal is kept at grain. The first-seen estimate is the earliest date
supported by two independent signals; otherwise it is the single signal with a
low-confidence label. Vendor launch dates (16 Oct 2025 for Anthropic) act as
floors for `SKILL.md`-format files.

| Signal | Strength | Weakness |
|---|---|---|
| Git first commit adding the file | Wide coverage | Dates can be set freely; imports and catalogue copies reset them. This repo's own lineage trace marked 217 of 261 clusters date-unreliable |
| Software Heritage content first-seen | Independent archive, keyed by the git blob SHA already stored | Only a lower bound; depends on archive crawl frequency |
| Copy-network direction | Orders copies relative to each other | Inherits git dating problems |
| Registry first-listed | Independent of git | Listing lags publication |
| Repo `created_at`, vendor announcements | Hard bounds | Coarse |

## Analytical dimensions

1. **Purpose:** what job the skill does, as a two-level taxonomy (domain, then
   task family).
2. **Concepts:** ideas expressed in the body, discovered by semantic
   classification. See [ADR 0005](../adr/0005-atlas-concept-method.md).
3. **Sophistication:** a ladder from L0 to L6, stored as features. See
   [ADR 0006](../adr/0006-atlas-sophistication-ladder.md).
4. **Lineage and morphing:** inherited spread (along a copy edge) is kept
   separate from convergent spread (independent emergence). Morphs are variant
   forms of one concept linked across a lineage.
5. **Context:** repo language, repo signature, location class (operational
   project or catalogue), agent platform by folder (`.claude`, `.codex`,
   `.agents`, `.github`, `.cursor`, `.gemini`), type of work, and industry with
   an explicit abstain option. Industry will be the least precise label.

**Vendor repackaging** is its own classification: verbatim mirror, light edit,
derivative or independent, against a reference set of every historical version
of vendor skills (`anthropics/skills`, `openai/skills` including
`.system/skill-creator`, OpenAI plugin repos, `vercel-labs/agent-skills` and
others found). Template influence, such as a skill scaffolded by skill-creator
that adds new ideas, is recorded separately and is not repackaging. Mirrors are
kept in the data but excluded from concept-growth counts.

## Data at the lowest grain

One table per entity, stable IDs, every derived row naming its method version.
Bulk tables go to Hugging Face and release assets; this repo holds code,
manifests and small tables. See [ADR 0007](../adr/0007-atlas-hosting-and-publication.md)
and the [data policy](../../DATA-POLICY.md).

| Table | Grain and key fields |
|---|---|
| `occurrence` | repo, path, blob SHA, SWHID, location class, platform folder, crawl source |
| `content` | blob SHA, front matter fields, size, repo license, excerpt pointer |
| `date_evidence` | content or occurrence, signal type, date, source URL, retrieved_at |
| `first_seen_estimate` | derived date, confidence, rule version |
| `purpose_label`, `context_label` | label, method, model and prompt version, confidence, evidence span |
| `concept` | ID, name, definition, status, created_in_release |
| `concept_observation` | content, concept, evidence span offsets, extractor, confidence |
| `sophistication_feature` | content, feature, value, detector version |
| `lineage_edge` | from, to, type (copy, edit, inherited-concept, convergent), source |
| `vendor_match` | content, vendor ancestor, class, similarity |

## Phases

| Phase | Delivers |
|---|---|
| 0 Scoping | This plan and ADRs 0003 to 0007 |
| 1 Exposition | GitSkills import, merge with Skill Map snapshots, vendor reference set, delta crawl, purpose and context labels, sophistication features, first site and FAQ |
| 2 Dating | Multi-signal date evidence, Software Heritage lookups, estimate rule, validation sample |
| 3 Concepts | Extraction, clustering, naming, taxonomy v1, accuracy check on about 200 skills |
| 4 Timeline and morphing | Growth curves, inherited versus convergent spread, morph catalogue |
| 5 Publication | Release with DOI, concept pages, guidelines, first article |

Every step lands as a pull request carrying a snapshot manifest (file hashes),
a short method note, tests and the regenerated report. A CI guard, like the
existing corpus guard, blocks headline numbers from drifting without a data
change.

## Extensions

- AGENTS.md, CLAUDE.md, Cursor rules and Copilot instructions as a sibling
  study linked by the same concept registry, giving the pre-history before
  October 2025.
- Concept graduation: when a community idea appears in the agentskills.io
  spec, skill-creator or vendor docs, with dates.
- Whether sophistication pays, joining ladder levels to
  [SkillsBench](https://arxiv.org/html/2602.12670v1) outcomes.
- A "does this exist?" MCP server over the registry.
- Monthly refresh with deltas. Custom GPTs once their content and dates are
  reachable.

## FAQ (draft)

**How are dates estimated?** From at least two independent signals where
possible, always labelled as estimates with a confidence level and the
evidence behind them.

**Is a copy of a vendor skill counted as a new skill?** It stays in the data,
classed as a mirror, light edit or derivative, and mirrors do not count toward
concept growth.

**Can I reuse the data?** Annotations are CC BY 4.0 and code is MIT. Skill text
stays under its authors' terms; see the [data policy](../../DATA-POLICY.md).

**Why isn't my repo here?** It may postdate the last crawl, be private, or have
been excluded on request.
