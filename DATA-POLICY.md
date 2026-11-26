# Data policy

This page says what third-party content the Skill Map stores, under what terms,
and how an author can ask for removal. It is the reference for every crawl,
dataset, and study in this repository, including the Skill Concepts Atlas.

## What the repository holds today

- **Crawl snapshots under [`crawls/`](crawls/) contain the full text of public
  `SKILL.md` files** (the `skill_md_content` field), alongside the repository,
  path, blob SHA, raw URL and repository metadata. They are kept so that every
  derived number can be recomputed from the exact text that was scored.
  Texts on the removal list (see below) have been taken out and only their
  pointer remains.
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
  dates, lineage edges), existing and future, are released under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), so they can be
  reused with attribution. [LICENSE-DATA.md](LICENSE-DATA.md) says what that
  covers and how to attribute. Short excerpts quoted inside annotations as
  evidence are not covered by CC BY 4.0; they stay under their authors' terms.

## Rules for new datasets and studies

These apply to everything published from now on, starting with the Skill
Concepts Atlas.

1. **Pointers first.** Every record identifies its source by repository, path,
   git blob SHA and, where available, a Software Heritage identifier (SWHID),
   so the original can be retrieved without this project redistributing it.
2. **Derived values, not copies.** Published tables carry labels, features,
   dates and edges, each with the method version that produced it.
3. **Short excerpts only.** Evidence quoted to support a label is limited to
   at most 300 characters per excerpt, at most 3 excerpts per source file, and
   at most 600 characters per source file in total, each with its pointer.
4. **Full text only where the license allows.** Full `SKILL.md` text is
   included in a published dataset only when the repository's license **and**
   the skill's own declared license (its frontmatter `license:` field, if any)
   are on the allow-list: MIT, MIT-0, Apache-2.0, BSD-2-Clause, BSD-3-Clause,
   0BSD, CC-BY-4.0, CC-BY-3.0 or CC0-1.0. A skill can carry stricter terms than
   its repository, so both are checked. The license name and the original
   copyright notice are recorded beside the text, as licenses such as MIT and
   Apache 2.0 require. Everything else is published as a pointer.
   [`crawlers/licensing.py`](crawlers/licensing.py) implements the check and the
   excerpt caps.
5. **Bulk data lives outside git history.** Large tables are published as
   Parquet and CSV on Hugging Face and as release assets, not committed here.
6. **Built for machine reuse.** Data is kept at the lowest grain, with stable
   identifiers and a data dictionary, on the assumption that people and
   automated agents will download and reuse it.

## The removal list

[`data/exclusions.json`](data/exclusions.json) lists what this project does not
redistribute, and [`crawlers/exclusions.py`](crawlers/exclusions.py) applies it.

- **Repositories** whose authors asked to be left out. Crawls skip them.
- **Texts**, by git blob SHA. Removal is by content, so every copy of an
  excluded text goes, whichever repository holds it. Crawls never store an
  excluded text.

Removing a text from a snapshot keeps the row and its pointer (repository,
path, blob SHA), sets `skill_md_content` to null, and records why in
`content_removed`. `python crawlers/exclusions.py --check` fails if any snapshot
still holds an excluded text.

On 2026-11-26 the list started with the 30 texts whose own frontmatter license
says proprietary or non-commercial. Copies of them sat in 78 snapshot rows
across 6 repositories (48 distinct skills), including Anthropic's document
skills and copies of those in other repositories. Their text was removed from
the snapshots.

Derived data in `data/` was computed before that removal and quotes none of
those texts. It will change slightly the next time the pipeline is rebuilt.

## Asking for removal

If you wrote a skill that appears here and want it removed, open a
[Remove my skills](https://github.com/dhk/skill-map/issues/new?template=remove-skill.yml)
issue, or email the maintainer through [dhk.io](https://www.dhk.io).

On a valid request (you control the source repository or are its author):

- the repository, or the specific texts, are added to the removal list, so
  future crawls skip them;
- `python crawlers/exclusions.py --apply` removes the text from the current
  snapshot files in `crawls/` (the pipeline itself never edits snapshots),
  derived data is then rebuilt with `crawlers/run_pipeline.py`, and published
  datasets drop it in their next release;
- the request and the date it was handled are recorded in the issue.

Git history keeps earlier commits of this repository. Rewriting history to
purge them is a separate step the maintainer decides case by case, and the
issue will say whether it was done.

## Decision record

The reasoning behind this policy is in
[ADR 0003](docs/adr/0003-data-redistribution-policy.md).
