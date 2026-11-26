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
| `content` | one distinct blob SHA | representative repo and path, name, description excerpt (300 characters at most), body size, scripts and references flags, first and last commit dates, commit count |
| `repo` | one repository | stars, forks, fork flag, language, license, whether the license permits redistributing text, created and pushed dates |

Every row in all three tables carries `source` (the dataset and resolved
revision) and `method_version`.

Before writing anything, the importer checks its keys and stops on any failure:
one representative row per blob SHA, no representative with an empty SHA,
unique repo and path per occurrence, unique repo names, and a repo row for every
occurrence. Repo names and licenses are matched without regard to case.

## What it leaves out, and why

- **File text and commit messages.** GitSkills releases its metadata under
  CC BY 4.0, but its `content` fields stay under each origin repository's
  license. Following the [data policy](../../DATA-POLICY.md), the import never
  reads them. Descriptions, which are part of the file, are cut to 300
  characters and flagged when cut.
- **Commit author codes.** GitSkills replaces authors with keyed one-way codes.
  The catalogue doesn't need them; lineage work can add them later.

## Pinning and provenance

The Hugging Face revision is pinned to commit `ebab174`, the short id shown on
the dataset's file page on 26 Nov 2026. The importer resolves it to the full
commit and stops if it resolves to anything else. The pin will be replaced with
the full 40-character commit once the first run can reach Hugging Face. It also checks the expected row
counts (3,797,117 artifacts and 282,200 repos, from the dataset card).

After a run, `data/atlas/gitskills/manifest.json` is committed. It records the resolved revision, every input
file with its size and hash, the columns read, output row counts and hashes,
and a summary. A `--local` run records the revision as `local` rather than a
path on the machine, and relies on the input file hashes. The Parquet outputs are not committed; they go to GitHub release assets, with a copy on
Hugging Face, with each Atlas release.

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
- `license_permits_text` uses a fixed list of permissive SPDX ids and treats a
  missing or `NOASSERTION` license as not permitting redistribution.
