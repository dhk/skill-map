# 3. Publish pointers and derived data, keep full text only where licensed

Date: 2026-11-26

## Status

Accepted

## Context

The crawl snapshots under `crawls/` store the full text of public `SKILL.md`
files (`skill_md_content`, 8,768 non-empty rows across three crawls). The
submission form and the community seed list told authors that nothing is
copied into this repository. The repository's MIT license could also be read as
covering that third-party text, which it cannot.

The Skill Concepts Atlas will publish much larger datasets, aimed at
researchers and at automated reuse. Most source repositories carry no license
or a license that does not clearly allow redistribution, and the largest prior
dataset (GitSkills, about 3.8 million files) states no license at all.

## Decision

- Correct the public wording: snapshots contain `SKILL.md` text, kept for
  reproducibility.
- State that MIT covers project code and documents only; third-party text keeps
  its author's terms. Project annotations are CC BY 4.0.
- For new datasets, publish pointers (repository, path, blob SHA, SWHID),
  derived values with method versions, and excerpts of at most 300 characters.
  Include full text only for repositories whose detected license allows it.
- Keep bulk data on Hugging Face and in release assets, not in git history.
- Offer a removal route: an issue template plus an exclusion list honoured by
  future crawls and releases.
- Leave the existing snapshots and git history in place. They are the evidence
  behind published numbers, and rewriting history would break that audit trail.

## Consequences

- The public claims now match what the repository holds.
- Reproducing Atlas results needs a fetch step that resolves pointers to text
  (from GitHub or Software Heritage), which the Atlas pipeline will provide.
- License detection becomes a required field in new crawls.
- Removal from git history is not automatic; requests that need it are handled
  case by case and recorded in the issue.
