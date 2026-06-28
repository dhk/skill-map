# Code Review — Response & Action List

Second-pass review of the changes in `docs/CODE-REVIEW.md`. I verified the
prototypes against live runs (pipeline green, score parity held at median 82.5,
WHEN +1pt from the better parser, all modules parse, re-run produced byte-identical
data JSON). **Verdict: sound, mergeable. No correctness changes are required.**

Markup for the other agent below. Inline markers carry the same tag — walk them
with `grep -rn "RECOMMEND(review2" .`. Priorities: **P0** = do before merge,
**P1** = should, **P2/backlog** = optional.

## P0 — before merge (one item)
| # | Where | Action |
|---|---|---|
| 1 | `docs/internal-skill-map.md:264` | Stale `1,119` skills. Update to the live count (4,975 files / ~3,769 unique). The branch's own generic `check_docs` flags it, so the pipeline's doc gate now fails on it. Inline marker added. |

## P1 — recommended polish
| # | Where | Action |
|---|---|---|
| 2 | `crawlers/patch_map_badges.py:37` | Join now refreshes only **26/39** graded map nodes (was 39/39). The other 13 keep *stale* grades from a prior run — the `source_url → (repo, file_path)` join drops rows after the merged-corpus/graphio changes. Fix the join and log `n/total` so a drop is visible. Inline marker added. |
| 3 | Deterministic tagger framing (`docs/CODE-REVIEW.md` §B, `classify_tags.py`) | Keep, but label honestly: all-4-axis agreement vs LLM is **12%** (per-axis 48–66%). It's a free *default + LLM-tail*, not parity — don't wire it to *replace* `tag_skills` outright; make the LLM pass the documented fallback for the ambiguous tail. |

## Backlog — the still-open inline `REVIEW(...)` notes, ranked
These were correctly left as notes by the first pass. My suggested order:
| Pri | Item | Where | Why |
|---|---|---|---|
| P1 | Thread `$GITHUB_TOKEN` into all unauth API calls | `fetch_siblings.py`, `lineage_trace.py`, `judge_llm.fetch_siblings` | 60 req/hr + bare `except` turns rate-limit exhaustion into silently-dropped data. `maturity_crawl.py` already does it — copy the pattern. Highest-risk open item. |
| P1 | Check the tree-API `truncated` flag | `crawl.py`, `fetch_siblings.py` | Recursive trees truncate at ~100k entries; today skills past the cutoff vanish silently on large monorepos. Log/raise on `truncated=True`. |
| P2 | One-crawl-per-day resumption | `crawl.py:find_today_dir` | Two different lists on the same day merge into one dir; metrics reflect only the last list. Suffix the dir by list_id or time. |
| P2 | Move `default_branch` capture fully upstream | `crawl.py`/`enrich_urls.py` | Prototype A captures it; finish removing the `/tree/main/` hard-codes so master/develop repos stop 404-ing source links. |
| P2 | Frozen rubric thresholds | `skill_quality.py` | Constants pinned from one anthropics snapshot; fine for now, but note they're not recomputed as the canonical set evolves. |
| P3 | `reclassify.py` domain map | `reclassify.py` | Counts now derived (good); the keyword `classify_domain()` is heuristic — acceptable, but flag it as the remaining hand-maintained surface. |

## Already done — do NOT re-flag
The first pass already landed these; verified present:
- Unique-skill count **is** folded into `STATS.md` (`gen_stats.py` lines 38–71) → "~3,769 unique skills."
- Numeric crawl sort (`_crawl_n`), `latest_content_by_key()`, judges/lineage off the crawl-1 pin.
- `graphio.py` shared by 5 scripts; PyYAML parse with hand-parser fallback (scores 99% identical).
- `track_history` scores with siblings; `enrich_urls` `(org,dir)` match; `git push -u origin <branch>`.

## Don't touch
`score_corpus` / `skill_quality` / `repo_signature` / `gen_stats` + `check_docs`
are clean and are the right "derive, don't hand-write" core. The committed derived
data is already consistent with a fresh pipeline run (only the Sankey PNG differs,
due to matplotlib timestamp metadata) — so no forced regen needed on merge.
