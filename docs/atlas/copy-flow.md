# Copy-flow diagrams

`atlas-copies.html` shows how skills published in vendor repositories are copied
into other GitHub repositories. It reads one file,
`data/atlas/vendor_reference/copy_flow.json`, written by
`crawlers/atlas/copy_flow.py` from the vendor reference tables.

## Build

```sh
uv run --with pyarrow python -m crawlers.atlas.vendor_reference --gitskills data/atlas/gitskills
uv run --with pyarrow python -m crawlers.atlas.copy_flow
```

The first step needs the GitSkills import on disk and writes `mirror.parquet`.
The second aggregates it. Open the page through any static server from the repo
root (for example `python -m http.server`), because browsers block `fetch` from
`file://`.

## What counts

- **Skill:** one vendor repository and `SKILL.md` path, as in `vendor_skill`.
- **Copy:** a GitSkills occurrence outside the vendor repositories whose text is
  byte-identical to any version of that skill (`vendor_mirror`). Edited copies
  are not counted, so every number is a floor.
- **Platform folder:** the agent folder the copy sits under (`.claude`,
  `.agents`, `.codex` and so on), from GitSkills' `platform_folder`.
- **Between vendors:** a skill first landing in one vendor repository and later
  appearing in another vendor's, from `cross_vendor`.

## What the file holds

Counts and pointers only: repository names, paths, dates, authorship labels and
copy counts. No skill text. Repositories on the removal list are dropped and
skills whose text is on it are flagged with `removal_listed`. The repository
list is capped (`--max-repos`, default 500, each copying at least
`--min-skills` distinct vendor skills, default 3), so the graph view shows the
heaviest copiers, not every copier; the vendor and skill totals are uncapped.

## Views

- **Publication view:** a Sankey from vendor to its most-copied skills to the
  platform folder the copies sit in. Skills below the cut are grouped per
  vendor. A second Sankey shows copies between vendors.
- **Explore the graph:** a force-directed graph of skills (coloured by vendor,
  sized by copying repositories) and the repositories that copy them. Zoom,
  drag, search, and click a node to isolate its neighbours.
- **Table:** the 200 most-copied skills, sortable.

Colours follow a fixed vendor order (Anthropic, OpenAI, Microsoft, Google,
Hugging Face, Vercel, Cloudflare; others gray), so a vendor keeps its colour
when others are filtered out.

GitSkills data is CC BY 4.0 (DOI 10.5281/zenodo.21875637).
