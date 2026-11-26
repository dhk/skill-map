# 5. Discover concepts by automated semantic classification

Date: 2026-11-26

## Status

Accepted (2026-11-26).

## Context

A "concept" in the Atlas is an idea expressed in a skill, such as an
anti-trigger, asking before mutating, or verifying one's own output. Published
taxonomies exist (Anatomy to Smells, How Agent Skills Evolve, this repo's
rubric flags), but starting from one would only find ideas someone already
named. Compute is plentiful, and the maintainer prefers full automation now
with hand-tuning later.

## Decision

1. An LLM extracts concept observations from every distinct skill text, each
   with its exact evidence span and a one-line normalised statement. A
   50,000-skill stratified sample runs first and reports its cost and accuracy;
   the full run waits for the maintainer's go-ahead on that cost.
2. Statements are embedded and clustered (for example HDBSCAN), and the run is
   repeated with a second embedding model.
3. An LLM names and defines each cluster; the pipeline applies merges and
   splits itself, producing taxonomy v1 with stable concept IDs. Taxonomy v1 is
   then frozen: new skills are assigned to the nearest existing concept, and
   ones that fit none are queued for the next taxonomy version.
4. Published taxonomies are used afterwards only as a crosswalk and coverage
   check.
5. Copies inherit observations by content hash, so each distinct text is
   processed once. Concept spread is counted once per near-copy family, not
   once per copy.
6. Validation: the maintainer labels one stratified sample (about 200 skills)
   across every dimension, purpose, context, industry, vendor match and
   concepts, to measure precision and recall, including what the model misses
   (it measures accuracy and does not gate the run);
   stability is measured across re-runs and across the two embedding models
   (adjusted Rand index); a held-out recent month tests whether new skills land
   in existing clusters.

## Consequences

- Every observation row records model, prompt and method versions, so a later
  run can be compared or replaced without rewriting evidence.
- Taxonomy versions are frozen; merges and splits keep provenance so concepts
  can be traced across versions.
- Accuracy is reported, not assumed, and the hand-labelled sample is the main
  human cost.
- Model spend is known from the 50,000-skill sample before it is committed.
