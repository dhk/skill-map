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

Every row carries `source` (the dataset and resolved revision) and, where it is
derived, `method_version`.

## What it leaves out, and why

- **File text and commit messages.** GitSkills releases its metadata under
  CC BY 4.0, but its `content` fields stay under each origin repository's
  license. Following the [data policy](../../DATA-POLICY.md), the import never
  reads them. Descriptions, which are part of the file, are cut to 300
  characters and flagged when cut.
- **Commit author codes.** GitSkills replaces authors with keyed one-way codes.
  The catalogue doesn't need them; lineage work can add them later.

## Pinning and provenance

The Hugging Face revision is pinned to commit `ebab174`, the id shown on the
dataset's file page on 26 Nov 2026. The importer resolves it to the full commit
and stops if it resolves to anything else. It also checks the expected row
counts (3,797,117 artifacts and 282,200 repos, from the dataset card).

`data/atlas/gitskills/manifest.json` records the resolved revision, every input
file with its size and hash, the columns read, output row counts and hashes,
and a summary. The Parquet outputs are not committed; they go to Hugging Face
and release assets with each Atlas release.

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

The remote read uses HTTP range requests and fetches only the listed columns,
so the text columns are never downloaded.

## Known limits

- GitSkills is a July 2026 snapshot and a lower bound: GitHub code search
  indexes default branches only, files under 384 KB, and forks only when they
  out-star the parent (from the dataset card).
- Commit dates exist for 458,548 files in standard locations plus a sample;
  they are one dating signal among several (see the [plan](plan.md)).
- `license_permits_text` uses a fixed list of permissive SPDX ids and treats a
  missing or `NOASSERTION` license as not permitting redistribution.
