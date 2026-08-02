# 2. Add CI guards against corpus spam and doc/data drift

<!-- Retroactive ADR: recorded after the fact, following a real incident. -->

Date: 2026-06 to 2026-07 (retroactively recorded; original changes: PR #1
incident and revert #23, Corpus Guard #24/#25, `check_docs.py` #17)

## Status

Accepted

## Context

A spam PR (#1, `Xquik-dev`) was merged and changed the published skill/repo
counts in the corpus data — nothing caught it before merge, and nothing
would have caught README's own badges or docs' headline numbers quietly
disagreeing with the actual data afterward. For a solo-maintained repo that
accepts outside contributions (skill submissions via issue template, PRs),
manual review alone isn't a reliable enough backstop against either bad-faith
edits or ordinary doc rot (a number hand-typed in prose, never updated after
the data changed).

## Decision

Add two independent, CI-enforced guards rather than relying on maintainer
vigilance:

- **Corpus Guard** (`corpus-guard.yml`): catches spam PRs and headline-number
  drift in the corpus data itself before merge. Marked safe to use as a
  required status check.
- **`check_docs.py`**: recomputes the load-bearing figures (skill count,
  repo count, median quality, WHEN-trigger %) directly from
  `data/corpus_stats.json` / `data/graph_data_v2.json`, and flags any
  narrative doc — including README's own badges and intro paragraph, not
  just `docs/` — that disagrees with that recomputed truth. Deliberately
  warns rather than auto-editing prose, since auto-rewriting narrative text
  is too fragile to trust unattended.

## Consequences

- A spam or careless PR that changes the corpus can no longer silently ship
  a wrong headline number — the same failure mode that motivated this can't
  recur unnoticed.
- `check_docs.py` only catches the specific figures it's told to check
  (skill count, repo count, quality, WHEN-trigger %, the interactive-graph
  line) — a new headline figure introduced in future docs needs an explicit
  addition to the checker, it isn't covered automatically.
- Because CODEOWNERS documents a solo maintainer, `required_approving_review_count`
  is 0 (to avoid a self-approval deadlock) — these automated guards are
  doing work a second human reviewer would otherwise do.
