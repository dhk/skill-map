# 5. Discover concepts by automated semantic classification

Date: 2026-11-26

## Status

Proposed. Becomes Accepted once DHK settles the open method decisions.

## Context

A "concept" in the Atlas is an idea expressed in a skill, such as an
anti-trigger, asking before mutating, or verifying one's own output. Published
taxonomies exist (Anatomy to Smells, How Agent Skills Evolve, this repo's
rubric flags), but starting from one would only find ideas someone already
named. Compute is plentiful, and the maintainer prefers full automation now
with hand-tuning later.

## Decision

1. An LLM extracts concept observations from every distinct skill text, each
   with its exact evidence span and a one-line normalised statement.
2. Statements are embedded and clustered (for example HDBSCAN), and the run is
   repeated with a second embedding model.
3. An LLM names and defines each cluster; the pipeline applies merges and
   splits itself, producing a versioned taxonomy with stable concept IDs.
4. Published taxonomies are used afterwards only as a crosswalk and coverage
   check.
5. Copies inherit observations by content hash, so each distinct text is
   processed once.
6. Validation: the maintainer checks a sample of about 200 skills to measure
   precision and recall (it measures accuracy and does not gate the run);
   stability is measured across re-runs and across the two embedding models
   (adjusted Rand index); a held-out recent month tests whether new skills land
   in existing clusters.

## Consequences

- Every observation row records model, prompt and method versions, so a later
  run can be compared or replaced without rewriting evidence.
- Taxonomy versions are frozen; merges and splits keep provenance so concepts
  can be traced across versions.
- Accuracy is reported, not assumed, and the 200-skill check is the main human
  cost.
