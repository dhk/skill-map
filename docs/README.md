# docs/ index

14 files plus two subfolders, four kinds. This page exists so you don't have
to open each one to find out which kind it is.

## Architecture & decisions — structure and why it's shaped this way

| Path | What it shows |
|---|---|
| [architecture/overview.md](architecture/overview.md) | C4-style context/container diagrams: the two products in this repo (the map site, skill-doctor/skill-audit) and how they relate. |
| [adr/](adr/) | Architecture Decision Records — immutable, one per real decision. Currently: why skill-doctor ships as a separate distributable product (0001), why Corpus Guard + `check_docs.py` exist (0002). |

See also [`../ROADMAP.md`](../ROADMAP.md) at repo root (themes, not this
index's scope, but the natural next stop after architecture).

## Auto-generated — regenerate with `python crawlers/run_pipeline.py`, don't hand-edit

| File | Generator | What it shows |
|---|---|---|
| [STATS.md](STATS.md) | `crawlers/gen_stats.py` | Live corpus snapshot — skill/repo counts, quality median. The source of truth other docs cite. |
| [adopted-conventions.md](adopted-conventions.md) | `crawlers/gen_conventions.py` | Convention-adoption rates: best practitioners vs. everyone else. |
| [originators.md](originators.md) | `crawlers/originator_leaderboard.py` | Leaderboard of who originates skills vs. who copies. |
| [curiosities.md](curiosities.md) | `crawlers/curiosities.py` | Per-crawl anomaly detectors — popular-but-undiscoverable, viral copies, coercive tone, etc. |
| [skill-wiring-study.md](skill-wiring-study.md) | `crawlers/discover_wiring.py` | Implicit cross-skill references mined from the corpus (8,249 edges). |

## Study — hand-written analysis, built on the auto-generated data above

| File | What it answers |
|---|---|
| [skill-best-practices-study.md](skill-best-practices-study.md) | Hub doc for the whole study — links everything below in reading order. |
| [best-practices.md](best-practices.md) | **Reference**: the scoring rubric itself — dimensions, weights, grades — derived empirically from `anthropics/skills` and `openai/skills`. Look here to know what "good" means. |
| [skill-ecosystem-vulnerabilities.md](skill-ecosystem-vulnerabilities.md) | **Explanation**: the full narrative research report the rubric and checklist are drawn from — corpus composition, quality distribution, defect inventory, safety vulnerabilities, methodology, what's next. Look here for the *why* and the full data; `best-practices.md` and `skill-author-checklist.md` don't repeat it, they each pull one actionable angle out of it (rubric vs. checklist). |
| [skill-types.md](skill-types.md) | Quality sliced by skill type (generator, reviewer, reference, etc). |
| [skill-author-checklist.md](skill-author-checklist.md) | **How-to**: the authoring checklist, tagged by what's machine-checkable vs. needs judgment. Look here when writing a skill, not when researching the ecosystem. |
| [llm-judge-tuning.md](llm-judge-tuning.md) | Post-mortem on why the LLM judge scored Anthropic "weak," and the fix. |
| [repo-signature-playbook.md](repo-signature-playbook.md) | "If your repo looks like X, do Y" — per-archetype recommendations. |
| [just-add-these-skills.md](just-add-these-skills.md) | The general-purpose skill set adopted across ≥4 independent repos. |
| [update-from-anthropic.md](update-from-anthropic.md) | Specific Anthropic skills that miss Anthropic's own rubric, with fixes. |
| [incremental-crawl-system.md](incremental-crawl-system.md) | How the pipeline stays current across re-crawls without hand-editing. |

## Planning & outreach — not part of the corpus study

| File | What it's for |
|---|---|
| [design-brief.md](design-brief.md) | UX review brief for the next map iteration (dated 2026-06-25). |
| [internal-skill-map.md](internal-skill-map.md) | Design doc for pointing the crawler at a corporate GitHub org. |
| [article-series.md](article-series.md) | Five-part article series outline built on this study. |
