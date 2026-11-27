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

The output is kept under 1 MB, because [ADR 0007](../adr/0007-atlas-hosting-and-publication.md)
keeps only small tables in git. If the default caps (400 skills, 500
repositories) come out larger, the export steps them down (300/300, 200/300,
150/200, 100/150 repositories/skills) and records the caps it used in
`meta.caps`. If even the smallest step is over 1 MB, it writes
`release/copy_flow.json` (gitignored) and exits with status 3, for a release
asset. The full grain stays in `mirror.parquet`. Open the page through any static server from the repo
root (for example `python -m http.server`), because browsers block `fetch` from
`file://`.

## What counts

- **Skill:** one vendor repository and `SKILL.md` path, as in `vendor_skill`.
- **Copy:** a GitSkills occurrence outside the vendor repositories whose text is
  byte-identical to any version of that skill (`vendor_mirror`). Edited copies
  are not counted, so every number is a floor.
- **Credit:** a vendor's own publication comes first, because that is the
  worked example people meet and reuse (DHK, 27 Nov 2026). Each text is
  credited to the earliest path where a vendor published it as its own
  (authorship first-party or unstated). Only a text no vendor published as its
  own goes to the earliest path whose plugin manifest or partner folder names
  another author, and its copies are tagged `credit: "repackaged"`, keeping
  that author in `manifest_author`. So OpenAI's plugins repository shipping
  Jesse Vincent's superpowers skills shows as "repackaged via OpenAI", not as
  OpenAI's work. When a vendor moves a skill or republishes the same text at
  another path, the copies stay with the first path, so the newer path can show
  zero copies even though its text is widely found.
- **Repackaged is strict for now:** a manifest that names a person counts as
  another author even in a vendor's own repository (for example three plugins
  in `anthropics/claude-code` that name individuals), because nothing in the
  repository says whether they are staff. A reviewed list of vendor staff would
  move those back; that waits on DHK.
- **Platform folder:** the agent folder the copy sits under (`.claude`,
  `.agents`, `.codex` and so on), from GitSkills' `platform_folder`.
- **Between vendors:** a skill first landing in one vendor repository and later
  appearing in another vendor's, from `cross_vendor`.

## What the file holds

Counts and pointers only: repository names, paths, dates, authorship labels,
credit and copy counts. Every vendor row splits its skills, files and copying
repositories by credit in `by_credit`, and vendors are ranked by the reach of
their own skills; `skills_rest` has one row per vendor and credit;
`totals.copies_by_credit` gives the split overall; each repository carries
`repackaged_copies`. No skill text. Repositories on the removal list are dropped. Each
file whose own text is on the removal list is counted in its skill's
`removal_listed_copies` (and `totals.copies_of_removal_listed_texts`), rather
than flagging a whole skill because one of its versions is listed.

Two lists are capped. `skills` holds the skills found in the most repositories
(`--max-skills`, default 400); every other copied skill is summed per vendor in
`skills_rest`, which the Sankey folds into each vendor's grouped node.
`repos` holds the repositories with the most distinct vendor skills
(`--max-repos`, default 500, each with at least `--min-skills`, default 3).
`edges` are `[skill index, repo index, files]` between those two lists only, so
the graph shows the heaviest holders, not every one. Vendor rows and `totals`
are uncapped.

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

Repackaged skills keep the colour of the vendor that shipped them, striped, and
sit below that vendor's own skills; the "Repackaged by a vendor" chip hides
them. The export refuses a `mirror.parquet` with no `credit` column, so an
export from before this rule can't be mixed in.

Colours follow a fixed vendor order (Anthropic, OpenAI, Microsoft, Google,
Hugging Face, Vercel, Cloudflare; others gray), so a vendor keeps its colour
when others are filtered out.

The page loads D3 and d3-sankey from jsDelivr with pinned integrity hashes, and
escapes every repository name, path and label before putting it in HTML.

GitSkills data is CC BY 4.0 (DOI 10.5281/zenodo.21875637).
