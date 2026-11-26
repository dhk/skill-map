# Method note: importing GitSkills as the base catalogue

Date: 2026-11-26 · Code: [`crawlers/atlas/gitskills.py`](../../crawlers/atlas/gitskills.py)
· Pin: [`crawlers/atlas/sources.json`](../../crawlers/atlas/sources.json)

## What it does

Reads the pinned release of [GitSkills](https://huggingface.co/datasets/mvaccargiu/gitskills)
(Destefanis, Graziotin, Vaccargiu and Ortu, [arXiv:2608.10906](https://arxiv.org/abs/2608.10906);
Zenodo DOI [10.5281/zenodo.21875637](https://doi.org/10.5281/zenodo.21875637),
version 1.0.0) and writes three Atlas tables:

| Table | Grain | Main fields |
|---|---|---|
| `occurrence` | one `SKILL.md` occurrence | repo, path, blob SHA, location class, platform folder, discovered_at |
| `content` | one distinct blob SHA | representative repo and path, name, description excerpt (300 characters at most, only where licensed) and why it was withheld otherwise, licence of the earliest copy and the repo it came from, body size, scripts and references flags, first and last commit dates, commit count |
| `repo` | one repository | stars, forks, fork flag, language, license, whether the license permits redistributing text, created and pushed dates |

Every row in all three tables carries `source` (the dataset and resolved
revision) and `method_version`. Each table's Parquet metadata carries the
CC BY 4.0 licence and attribution for the annotations and for GitSkills, with
a note that description excerpts stay under their authors' terms.

Before writing anything, the importer checks its keys and stops on any failure:
one representative row per blob SHA, no representative with an empty SHA,
unique repo and path per occurrence, unique repo names, and a repo row for every
occurrence. Repo names and licenses are matched without regard to case.

## What it leaves out, and why

- **File text and commit messages.** GitSkills releases its metadata under
  CC BY 4.0, but its `content` fields stay under each origin repository's
  license. Following the [data policy](../../DATA-POLICY.md), the import never
  reads them.
- **Descriptions without a licence that allows them.** A description is part of
  the file, so it is published (cut to 300 characters and flagged when cut)
  only when the licence of the text's earliest copy is on the allow-list in
  [`crawlers/licensing.py`](../../crawlers/licensing.py). Otherwise the row
  keeps its pointer and `description_withheld` says `licence`. The earliest
  copy is the one with the earliest git first-commit date; when no copy has
  one, it is the copy whose repository was created first.
- **Anything on the removal list.** Repositories in
  [`data/exclusions.json`](../../data/exclusions.json) are dropped from all
  three tables; if that removes a text's representative, another copy takes
  its place. Texts listed by blob SHA keep only their pointer, with
  `description_withheld` set to `removal-list`. The run stops if the list is
  missing, and the manifest records its hash and what it removed.
- **Commit author codes.** GitSkills replaces authors with keyed one-way codes.
  The catalogue doesn't need them; lineage work can add them later.

## Pinning and provenance

GitSkills is read from Hugging Face, which can serve single columns without the
44 GB Zenodo database, and cited by its Zenodo DOI. The Hugging Face revision is
pinned to the full commit `ebab17454a7c236f8f26b183567f1a126f42e3f8`, which the
first run on 26 Nov 2026 resolved from the short id `ebab174` shown on the
dataset's file page. The importer stops if the pin resolves to anything else.
It also checks the expected row counts before any merging (3,797,117 artifacts
and 282,200 repos, from the dataset card).

## First run (26 Nov 2026)

From the committed manifest: 3,797,113 occurrences, 1,877,980 distinct texts
and 282,191 repositories after merging 9 repository names that differed only
by case (4 occurrences shared a path across two spellings). Descriptions are
published for 753,797 texts (40%), withheld for licence on 1,124,160 and for
the removal list on 23. 4,468 of the 4,759 blob SHAs in this repo's own
snapshots (94%) are also in GitSkills.

The dataset card's 1,877,981 distinct texts is one more than ours. The
missing text is the one merge that lost a text: `lzzmm/gpubk` and `lzzmm/GPUbk`
both list `src/bk/data/codex-skill/gpubk/SKILL.md`, with different contents
(`f5b619f2…` and `3d4d8455…`). They are one repository seen twice, so only one
row can stand for that path; the importer kept `3d4d8455…`, and `f5b619f2…`
appears nowhere else in the release. The other 3 merged occurrences had the
same text under both spellings. A dropped text is an older version of a file
that is still catalogued, so it is left out rather than kept without an
occurrence.

After a run, `data/atlas/gitskills/manifest.json` is committed. It records the resolved revision, every input
file with its size and hash, the columns read, output row counts and hashes,
and a summary. A `--local` run records the revision as `local` rather than a
path on the machine, and relies on the input file hashes. The Parquet outputs are not committed; they go to GitHub release assets, with a copy on
Hugging Face, with each Atlas release.

## Repository names that differ only by case

GitHub treats `owner/name` case-insensitively, and the GitSkills repos table
has rows that differ only by case (9 in the release read on 26 Nov 2026),
which would otherwise break the one-row-per-repo key. The importer keeps one
row per name: the latest `pushed_at`, then the most stars, then the spelling
that sorts first. Occurrences under any spelling move to the kept one. Where
that leaves two occurrences with the same repo and path, it keeps the
representative row, then the latest `discovered_at`. The manifest's
`duplicate_repo_names` section lists every merged repository and counts the
merged occurrences, with examples.

## Resuming

Each remote data file's selected columns are saved under
`data/atlas/gitskills/.cache/` as soon as they arrive, next to a small record
of the revision, file size, file hash and column list. A later run reuses a
saved file only when all four match, so an interrupted import picks up where
it stopped. `--no-cache` reads everything again.

## Platform folder

The agent platform is inferred from the first dot-folder in the path:
`.claude`, `.codex`, `.agents`, `.github`, `.cursor`, `.gemini`, `.windsurf`,
`.opencode` or `.kiro`; anything else is `other`. This is a context label, not
proof of which agent runs the skill.

## Overlap with this repo's snapshots

The summary counts how many blob SHAs in this repo's own crawl snapshots also
appear in GitSkills. That shows how much of the June corpus GitSkills already
covers, before the delta crawl adds August to November.

## Running it

```bash
pip install pyarrow huggingface_hub
python -m crawlers.atlas.gitskills              # reads the pinned revision over HTTP
python -m crawlers.atlas.gitskills --local DIR  # DIR holds artifacts/ and repos/ parquet folders
python -m pytest crawlers/atlas/tests
```

The remote read asks only for the listed columns, using HTTP range requests, so
the text columns are not read. Parquet footers and some read-ahead bytes are
still fetched, so the transfer is small but not exactly the listed columns.

## Known limits

- GitSkills is a July 2026 snapshot and a lower bound: GitHub code search
  indexes default branches only, files under 384 KB, and forks only when they
  out-star the parent (from the dataset card).
- Commit dates exist for 458,548 files in standard locations plus a sample;
  they are one dating signal among several (see the [plan](plan.md)).
- `license_permits_text` uses the data policy's allow-list and treats a
  missing or `NOASSERTION` license as not permitting redistribution.
- The skill's own frontmatter licence can't be checked here, because the import
  never reads the text. It is checked when text is fetched for later phases;
  until then, only the repository licence and the removal list gate a
  description.
