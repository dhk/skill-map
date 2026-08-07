# Documentation index

The repository documentation falls into four groups. Generated documents name
their generator and should not be edited by hand.

## Architecture and decisions

| Path | What it explains |
|---|---|
| [`architecture/overview.md`](architecture/overview.md) | System context and containers for the Skill Map, skill-doctor, pipeline, and CI guards |
| [`adr/`](adr/) | Immutable architecture decision records |
| [`../ROADMAP.md`](../ROADMAP.md) | Current product and engineering themes |

Start with the architecture overview when changing boundaries between the site,
crawler, corpus, and distributed tool.

## Generated evidence

Regenerate these documents with `python crawlers/run_pipeline.py`. Do not edit
them directly.

| Path | Generator | Output |
|---|---|---|
| [`STATS.md`](STATS.md) | `crawlers/gen_stats.py` | Current corpus counts and quality summary |
| [`adopted-conventions.md`](adopted-conventions.md) | `crawlers/gen_conventions.py` | Convention adoption rates |
| [`originators.md`](originators.md) | `crawlers/originator_leaderboard.py` | Skill originators and copies |
| [`curiosities.md`](curiosities.md) | `crawlers/curiosities.py` | Per-crawl anomalies and outliers |
| [`skill-wiring-study.md`](skill-wiring-study.md) | `crawlers/discover_wiring.py` | Implicit cross-skill references |

Generated findings derive from immutable snapshots under [`../crawls/`](../crawls/)
and intermediate data under [`../data/`](../data/).

## Research and guidance

Read [`skill-best-practices-study.md`](skill-best-practices-study.md) first for
the study’s evidence trail and recommended reading order.

| Path | Question answered |
|---|---|
| [`best-practices.md`](best-practices.md) | What does the empirical scoring rubric consider good? |
| [`skill-ecosystem-vulnerabilities.md`](skill-ecosystem-vulnerabilities.md) | What defects and safety gaps appear across the corpus, and why do they matter? |
| [`skill-author-checklist.md`](skill-author-checklist.md) | What should an author check before publishing? |
| [`skill-types.md`](skill-types.md) | How does quality differ by skill type? |
| [`llm-judge-tuning.md`](llm-judge-tuning.md) | Why did the first LLM judge mis-score strong skills, and how was it corrected? |
| [`repo-signature-playbook.md`](repo-signature-playbook.md) | What should a repository do given its current skill pattern? |
| [`just-add-these-skills.md`](just-add-these-skills.md) | Which general-purpose skills recur across independent repositories? |
| [`update-from-anthropic.md`](update-from-anthropic.md) | Which Anthropic skills miss parts of the derived rubric? |
| [`incremental-crawl-system.md`](incremental-crawl-system.md) | How does the corpus update without rewriting historical evidence? |

The rubric, checklist, and narrative report are complementary. They do not need
to repeat one another: the rubric defines scoring, the checklist supports
authors, and the report preserves the analysis.

## Planning and outreach

These documents describe proposed or communicative work rather than current
corpus evidence.

| Path | Purpose |
|---|---|
| [`design-brief.md`](design-brief.md) | Dated UX brief for a future map iteration |
| [`internal-skill-map.md`](internal-skill-map.md) | Design for applying the crawler to a private organization |
| [`article-series.md`](article-series.md) | Article-series outline derived from the research |

Treat dated planning documents as historical context unless the roadmap or an
open issue confirms that the work is active.
