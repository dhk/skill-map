# Method note: the August to November 2026 delta crawl

Date: 2026-11-27 · Code: [`crawlers/atlas/delta.py`](../../crawlers/atlas/delta.py)
· Decision: [ADR 0004](../adr/0004-atlas-scope-and-corpus.md)

## What it does

GitSkills is a snapshot taken in July and August 2026. The delta crawl looks
again with the same method and says what changed since:

- **New text:** a blob SHA GitSkills never saw. It was written or edited after
  the snapshot, or GitHub indexed it since.
- **New occurrence:** a known blob SHA at a repository and path GitSkills didn't
  list, which is a new copy of a known text.
- **Changed in place:** a path GitSkills listed whose blob SHA is now different.
  The row keeps the old SHA in `previous_blob_sha`.
- **Gone:** a GitSkills occurrence the crawl didn't find. Only meaningful when
  the manifest says `gone_is_reliable: true` (see below).

No file text is fetched. Code search returns each file's repository, path and
blob SHA, which is all the diff needs.

## How it searches

It follows GitSkills' collection method ([arXiv:2608.10906](https://arxiv.org/abs/2608.10906),
and the dataset card on Hugging Face), so the two snapshots are comparable:

1. Query `filename:SKILL.md` over the whole indexed size range,
   `size:0..393215`. GitHub only indexes files under 384 KB, and one query
   returns at most 1,000 results
   ([GitHub REST docs, "Search code"](https://docs.github.com/en/rest/search/search#search-code)).
2. If the reported total is 900 or more, split the size range into 2 to 16
   equal parts, more parts the bigger the total, and queue them.
3. Otherwise page through the results, 100 a page. If paging still reaches
   1,000 results, split anyway, because `total_count` is unreliable: the
   GitSkills card reports about 349,000 for the filename query against more
   than 3.8 million files retrieved.
4. A range one byte wide that still reaches 1,000 can't be split by size. That
   happens when one text has been copied more than 1,000 times. It is marked
   `capped` and re-queried with each of these path qualifiers: `.claude`,
   `.agents`, `.codex`, `.cursor`, `.github`, `.opencode`, `.gemini`, `.kiro`,
   `.windsurf`, `skills`, `plugins`. Results are merged by repository and path.
   This is best effort: copies outside those folders past the first 1,000 are
   missed, and the manifest lists every capped range.

Code search matches the basename without regard to case, so `skill.md` comes
back too. Rows carry `basename_exact` so a later step can drop or keep them,
as the GitSkills import does.

## Pace and cost

Code search allows 10 requests a minute for a signed-in user (same GitHub
page), and the client waits 6.5 seconds between calls. With at least 3.8
million files at 100 a page, the crawl needs at least 38,000 page requests plus
the probes that split ranges. At 10 a minute that is roughly 3.5 days or more
of wall clock. It costs no money. It uses one GitHub account and one token, on
purpose: spreading the search over several accounts to beat the limit would
break GitHub's terms.

On a 403 or 429 the client waits for `Retry-After` or the rate-limit reset; on
a 5xx or a network error it backs off up to 5 minutes, and gives up on a page
after 8 tries. A query GitHub refuses outright (422) marks that range `failed`
and the crawl moves on.

## Resuming

Progress lives in `data/atlas/delta/.cache/state.sqlite` (kept out of git). A
range is saved only once all its pages are in, so stopping with Ctrl-C, a
sleep or a crash loses at most the range in flight. Running the same command
again carries on.

## Outputs

In `data/atlas/delta/`. The Parquet files stay out of git like the other Atlas
tables; `manifest.json` is committed.

| File | Grain | Main fields |
|---|---|---|
| `occurrence.parquet` | one `SKILL.md` found now | repo, path, blob SHA, platform folder, `basename_exact`, size range, `new_text`, `new_occurrence`, `previous_blob_sha`, `removal_listed` |
| `gone.parquet` | one GitSkills occurrence not found now | repo, path, blob SHA |
| `manifest.json` | the run | method version, query, start and finish, requests, ranges by status, capped and failed ranges, ranges with incomplete results, `gone_is_reliable`, the GitSkills revision compared against, counts, removal-list and output hashes |

`gone_is_reliable` is true only when the crawl finished with no capped, failed
or incomplete range. Otherwise a missing file may just be one the search
couldn't reach, so `gone` is a list of candidates, not deletions.

Repositories on the removal list (`data/exclusions.json`) are left out of both
tables. Files whose text is on it are kept as pointers and flagged
`removal_listed`.

## What it doesn't do yet

- **Licences and dates for new repositories.** Code search doesn't return a
  repository's licence, stars or creation date. ADR 0004 asks for licence
  detection on new material; that is a follow-up pass over the new
  repositories through the GitHub API, sized once this crawl says how many
  there are.
- **First-commit dates for new texts.** Same follow-up.

## Running it

From the repository root, with `gh auth login` done or `GITHUB_TOKEN` set, and
the GitSkills import already run (it needs `data/atlas/gitskills/occurrence.parquet`):

```
uv run --with pyarrow python -m crawlers.atlas.delta --max-requests 60   # a trial, about 7 minutes
uv run --with pyarrow python -m crawlers.atlas.delta                     # the full crawl, resumable
uv run --with pyarrow python -m crawlers.atlas.delta --finish-only       # rebuild outputs from saved progress
```
