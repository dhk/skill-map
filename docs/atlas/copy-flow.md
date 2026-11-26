# Copy-flow diagrams

`atlas-copies.html` shows where texts that vendors published as skills also
appear in other GitHub repositories. It reads one file,
`data/atlas/vendor_reference/copy_flow.json`, written by
`crawlers/atlas/copy_flow.py` from the vendor reference tables.

## Build

```sh
uv run --with pyarrow python -m crawlers.atlas.vendor_reference --gitskills data/atlas/gitskills
uv run --with pyarrow python -m crawlers.atlas.copy_flow
```

The first step needs the GitSkills import on disk and writes `mirror.parquet`
and its hash into `manifest.json`. The second refuses to run unless the
manifest has a `mirror` section and every input table matches the hash the
manifest records, so a `mirror.parquet` left from an older run can't slip in.
It records those hashes in `meta.inputs_sha256`.

If the output is over 1 MB it is written to `release/copy_flow.json`
(gitignored) and the command exits with status 3: lower `--max-repos`, or
attach the file to a release, as [ADR 0007](../adr/0007-atlas-hosting-and-publication.md)
puts bulk tables in release assets rather than git. Open the page through any static server from the repo
root (for example `python -m http.server`), because browsers block `fetch` from
`file://`.

## What counts

- **Skill:** one vendor repository and `SKILL.md` path, as in `vendor_skill`.
- **Copy:** a GitSkills occurrence outside the vendor repositories whose text is
  byte-identical to any version of that skill (`vendor_mirror`). Edited copies
  are not counted, so every number is a floor.
- **Credit:** each text is credited only to the earliest vendor path that
  published it. When a vendor moves a skill or republishes the same text at
  another path, the copies stay with the first path, so the newer path can show
  zero copies even though its text is widely found.
- **Platform folder:** the agent folder the copy sits under (`.claude`,
  `.agents`, `.codex` and so on), from GitSkills' `platform_folder`.
- **Between vendors:** a skill first landing in one vendor repository and later
  appearing in another vendor's, from `cross_vendor`.

## What the file holds

Counts and pointers only: repository names, paths, dates, authorship labels and
copy counts. No skill text. Repositories on the removal list are dropped. Each
file whose own text is on the removal list is counted in its skill's
`removal_listed_copies` (and `totals.copies_of_removal_listed_texts`), rather
than flagging a whole skill because one of its versions is listed. The repository
list is capped (`--max-repos`, default 500, each copying at least
`--min-skills` distinct vendor skills, default 3), so the graph view shows the
heaviest copiers, not every copier; the vendor and skill totals are uncapped.

## Views

- **Publication view:** a Sankey from vendor to its skills found in the most
  repositories to the platform folder the files sit in. Skills below the cut
  are grouped per vendor. Skills are ranked by repositories in every view; band
  width is files, because files add up across the three columns and
  repositories don't (one repository can hold a skill in several folders). A
  second Sankey shows copies between vendors. This view shows counts only;
  copying repositories are named only in the graph.
- **Explore the graph:** a force-directed graph of skills (coloured by vendor,
  sized by copying repositories) and the repositories that copy them. Zoom,
  drag, search, and click a node to isolate its neighbours.
- **Table:** the 200 skills found in the most repositories, sortable.

Colours follow a fixed vendor order (Anthropic, OpenAI, Microsoft, Google,
Hugging Face, Vercel, Cloudflare; others gray), so a vendor keeps its colour
when others are filtered out.

The page loads D3 and d3-sankey from jsDelivr with pinned integrity hashes, and
escapes every repository name, path and label before putting it in HTML.

GitSkills data is CC BY 4.0 (DOI 10.5281/zenodo.21875637).
