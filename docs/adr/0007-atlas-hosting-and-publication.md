# 7. Host Atlas data on Hugging Face and pages on dhk.io

Date: 2026-11-26

## Status

Proposed. Becomes Accepted once DHK settles the open method decisions.

## Context

The Atlas will produce tables far larger than the existing crawl snapshots,
which already take about 90 MB on disk in this repository. The output is meant
for citation and for reuse by people and automated agents.

## Decision

- Code, manifests, method notes and small tables live in this repository.
- Bulk tables are published as Parquet and CSV in GitHub release assets on
  this repository, with a copy on Hugging Face, and are not committed to git.
- The write-up and browsable pages (concepts, purposes, notable skills) are
  static pages on dhk.io, searched with Pagefind. Datasette Lite may follow.
- If per-skill pages run into the millions, phase 1 falls back to pages for
  concepts, purposes and notable skills, with full skill search through the
  Hugging Face dataset viewer.
- Each release gets a Zenodo DOI, a datasheet, `CITATION.cff`, schema.org
  `Dataset` JSON-LD, `llms.txt` and a sitemap.
- Licensing follows the [data policy](../../DATA-POLICY.md): code MIT,
  annotations CC BY 4.0, skill text under its authors' terms.

## Consequences

- Reproducing a figure needs the release's data download, identified by DOI
  and manifest hash.
- Publishing to Hugging Face, Zenodo and dhk.io are public steps that wait for
  the maintainer's go-ahead.
