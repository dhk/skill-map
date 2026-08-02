# Roadmap

Themes, not dated commitments — see the [issue tracker](https://github.com/dhk/skill-map/issues)
for granular, current task tracking. Revisited per work cycle, not continuously.

## Now

- **Harden skill-doctor's distribution.** It ships three ways today (pipx/PyPI,
  Claude Code plugin marketplace, claude.ai zip) and recent work has been
  closing gaps in that surface: repo-free pip install, direct-debug workflow
  dispatch for the PyPI publish action, correct `id-token` permission
  propagation through the reusable workflow.
- **Protect corpus integrity.** Corpus Guard (catching spam PRs and headline-
  number drift before merge) shipped after a real incident (a spam PR briefly
  changed the published skill/repo counts). `check_docs.py` extends the same
  principle to narrative docs, including README's own badges.

## Next

- **Give skill-audit (and optionally skill-doctor) a real UI**, not just
  CLI/GitHub Action output — [#19](https://github.com/dhk/skill-map/issues/19).
- **Add a GitLab adapter** for skill-audit's `collect_github()` so audits
  aren't GitHub-only — [#18](https://github.com/dhk/skill-map/issues/18).
- **Resolve positioning** between skill-map/skill-doctor and adjacent tools
  like praxis — same audience, different pitch, or genuinely different tools?
  ([#20](https://github.com/dhk/skill-map/issues/20), [#21](https://github.com/dhk/skill-map/issues/21))

## Later

- **Refine repo type/signature detection** (`repo_signature.py`) as more
  repo shapes show up in the corpus — [#3](https://github.com/dhk/skill-map/issues/3).
- **Close the reproducibility gap** flagged inline in
  [`run_pipeline.py`](crawlers/run_pipeline.py): fold the hand-run,
  non-deterministic-adjacent steps (`tag_skills.py`, `sample_llm.py`,
  `judge_llm.py`, `reclassify.py`, `enrich_urls.py`) into the pipeline, or add
  `check_docs`-style staleness guards for them.
- Build toward one or more of the five negative-space territories the map
  itself identifies (session layer, skill discovery, skill evaluation) —
  unscheduled, dependent on where DHK's own attention goes next.
