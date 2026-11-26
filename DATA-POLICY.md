# Data policy

This page says what third-party content the Skill Map stores, under what terms,
and how an author can ask for removal. It is the reference for every crawl,
dataset, and study in this repository, including the Skill Concepts Atlas.

## What the repository holds today

- **Crawl snapshots under [`crawls/`](crawls/) contain the full text of public
  `SKILL.md` files** (the `skill_md_content` field), alongside the repository,
  path, blob SHA, raw URL and repository metadata. They are kept so that every
  derived number can be recomputed from the exact text that was scored.
- **Derived data under [`data/`](data/)** holds scores, labels, lineage edges,
  dates and other values computed from those snapshots. Some derived files
  quote short passages.
- **Seed lists under [`crawlers/crawl-lists/`](crawlers/crawl-lists/)** hold
  references (repository names and URLs) only.

Earlier wording in the submission form and the community seed list said that
no skill content is copied into this repository. That was wrong for the crawl
snapshots and has been corrected.

## Licensing

- The [MIT License](LICENSE) covers the code and the documents written for this
  project. It does **not** relicense third-party content.
- Each `SKILL.md` text in `crawls/` remains under its author's own terms, as set
  by the source repository. A snapshot copy grants no new rights to it.
- Annotations produced by this project (labels, scores, concept assignments,
  dates, lineage edges) are released under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) from the Skill
  Concepts Atlas onward, so they can be reused with attribution. Short excerpts
  quoted inside annotations as evidence are not covered by CC BY 4.0; they stay
  under their authors' terms.

## Rules for new datasets and studies

These apply to everything published from now on, starting with the Skill
Concepts Atlas.

1. **Pointers first.** Every record identifies its source by repository, path,
   git blob SHA and, where available, a Software Heritage identifier (SWHID),
   so the original can be retrieved without this project redistributing it.
2. **Derived values, not copies.** Published tables carry labels, features,
   dates and edges, each with the method version that produced it.
3. **Short excerpts only.** Evidence quoted to support a label is limited to a
   short span (at most 300 characters per excerpt) with its pointer.
4. **Full text only where the license allows.** Full `SKILL.md` text is
   included in a published dataset only for repositories whose detected license
   permits redistribution, and the license name and the original copyright
   notice are recorded beside the text, as licenses such as MIT and Apache 2.0
   require.
5. **Bulk data lives outside git history.** Large tables are published as
   Parquet and CSV on Hugging Face and as release assets, not committed here.
6. **Built for machine reuse.** Data is kept at the lowest grain, with stable
   identifiers and a data dictionary, on the assumption that people and
   automated agents will download and reuse it.

## Asking for removal

If you wrote a skill that appears here and want it removed, open a
[Remove my skills](https://github.com/dhk/skill-map/issues/new?template=remove-skill.yml)
issue, or email the maintainer through [dhk.io](https://www.dhk.io).

On a valid request (you control the source repository or are its author):

- the repository is added to an exclusion list so future crawls skip it;
- its text is removed by hand from the current snapshot files in `crawls/`
  (the pipeline never edits snapshots), derived data is then rebuilt with
  `crawlers/run_pipeline.py`, and published datasets drop it in their next
  release;
- the request and the date it was handled are recorded in the issue.

Git history keeps earlier commits of this repository. Rewriting history to
purge them is a separate step the maintainer decides case by case, and the
issue will say whether it was done.

## Decision record

The reasoning behind this policy is in
[ADR 0003](docs/adr/0003-data-redistribution-policy.md).
