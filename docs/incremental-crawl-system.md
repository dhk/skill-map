# Incremental Crawl & Findings System

How the study stays alive across re-crawls: each sweep is a snapshot, and a small
pipeline recomputes every finding, tracks what changed, and surfaces what's new,
novel, or odd. Designed so adding a crawl never means hand-editing the study.

## The snapshot model

Each crawl writes an immutable `crawls/crawl-N-DATE/data.json` (full SKILL.md
content + `file_sha` per file). Snapshots are never mutated — re-crawling creates
a new one. Every downstream tool reads **all** snapshots and merges them
(newest `file_sha` wins per `(repo, file_path)`), so the corpus only grows.

## The pipeline (run after any crawl)

```bash
python crawlers/crawl.py crawl --crawl-list <list.md|json>   # 1. new snapshot
python crawlers/fetch_siblings.py                            # 2. folder contents
python crawlers/score_corpus.py                              # 3. re-score everything
python crawlers/track_history.py                             # 4. per-skill timeline + delta
python crawlers/lineage_trace.py                             # 5. copy/lineage (if repos overlap)
python crawlers/curiosities.py                               # 6. the oddities report
```

| Stage | Tool | Produces | Idempotent? |
|---|---|---|---|
| crawl | `crawl.py` | `crawls/crawl-N-*/data.json` | append-only |
| siblings | `fetch_siblings.py` | `data/sibling_files.json` | yes (re-fetch) |
| score | `score_corpus.py` | `data/skill_quality.json` | yes |
| history | `track_history.py` | `data/skill_history.json` | yes (rebuilds from snapshots) |
| lineage | `lineage_trace.py` | `data/lineage.json` | yes |
| curiosities | `curiosities.py` | `docs/curiosities.md` | yes |

Everything recomputes from the snapshots, so the pipeline is **replayable**: blow
away the `data/*.json` derivatives and rerun to get identical output.

## What changes most — the history engine

`track_history.py` maintains a per-skill timeline — first seen, last seen,
`file_sha` history, quality history — and emits a per-crawl **delta**:

- **added / changed / removed**, scoped *per repo* so a crawl that only touches
  new repos doesn't false-flag old skills as removed.
- **top movers** — skills whose quality shifted most between snapshots (by SHA
  change), so a re-crawl of `anthropics/skills` immediately shows which skills
  improved or regressed.
- **repos added**.

Change detection keys on `file_sha`, so it's exact: an unchanged file is skipped,
a changed one re-scored and diffed.

## What's novel — and what's odd

`curiosities.py` is the reader-facing layer (`docs/curiosities.md`). It recomputes
a set of anomaly detectors each run, so the oddities stay current:

- ⭐ popular-but-undiscoverable (stars ≫ trigger discipline)
- 🦠 most-copied skills (viral) · 🌱 small-origin/big-spread ancestors
- 😤 coercive tone · 🏷️ invented control tags
- 📏 extremes (longest skill, deepest folder)
- ⚠️ high-stakes-without-guardrails
- ✅ the rare anti-trigger writers · 🎭 delightful names
- 🔀 **same skill, different grade** — copies that diverged (one repo kept the
  reference files, the copy dropped them)
- 🆕 what's new since the last crawl (straight from the history delta)

## Adding repos

Crawl lists are JSON **or** Markdown (`crawlers/crawl-lists/*.md`, a YAML
frontmatter + a `repo | type | tier | notes` table). Tag the `type` honestly —
`aggregator` / `prompt-registry` / `tool` repos aren't SKILL.md collections and
the crawl will (correctly) pull 0 skills from them.

## What a re-crawl unlocks that one crawl can't

A single snapshot can't see *motion*. Re-crawling the same repos turns on:
- **drift** — which skills are being actively improved vs left to rot,
- **regressions** — a skill that got worse (the `top_movers` with negative deltas),
- **real maturity** — iteration measured by `file_sha` changes across snapshots,
  the honest version of the commit-count proxy that
  [bulk-publishing broke](llm-judge-tuning.md).

The next high-value sweep is re-crawling the canonical repos (Anthropic has pushed
since the June-24 snapshot) to light up the first real delta.
