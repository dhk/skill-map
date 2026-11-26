# 3. Publish pointers and derived data, keep full text only where licensed

Date: 2026-11-26

## Status

Accepted

## Context

The crawl snapshots under `crawls/` store the full text of public `SKILL.md`
files (`skill_md_content`: 8,768 non-empty rows across three crawls, holding
4,341 unique texts from 43 repositories). The
submission form and the community seed list told authors that nothing is
copied into this repository. The repository's MIT license could also be read as
covering that third-party text, which it cannot.

The Skill Concepts Atlas will publish much larger datasets, aimed at
researchers and at automated reuse. Many source repositories carry no license
or one that does not clearly allow redistribution. The largest prior dataset,
GitSkills (about 3.8 million files), releases its metadata under CC BY 4.0 and
leaves file text under each origin repository's license, the same split this
policy adopts.

## Decision

- Correct the public wording: snapshots contain `SKILL.md` text, kept for
  reproducibility.
- State that MIT covers project code and documents only; third-party text keeps
  its author's terms. Project annotations, existing and future, are CC BY 4.0,
  stated in a data license file.
- For new datasets, publish pointers (repository, path, blob SHA, SWHID),
  derived values with method versions, and excerpts of at most 300 characters
  each, capped per source file. Include full text only when both the
  repository's license and the skill's own declared license are on an
  allow-list of permissive licenses.
- Keep bulk data on Hugging Face and in release assets, not in git history.
- Offer a removal route: an issue template plus a removal list, applied by
  content (blob SHA) across every repository and honoured by future crawls and
  releases.
- Remove now, from the existing snapshots, the texts whose own license says
  proprietary or non-commercial, keeping their pointers.
- Otherwise leave the existing snapshots and git history in place. They are the
  evidence behind published numbers, and rewriting history would break that
  audit trail.

## Consequences

- The public claims now match what the repository holds.
- Reproducing Atlas results needs a fetch step that resolves pointers to text
  (from GitHub or Software Heritage), which the Atlas pipeline will provide.
- License detection, for the repository and for the skill's own frontmatter,
  becomes a required field in new crawls.
- Derived numbers computed before the first removals will shift slightly at the
  next pipeline rebuild.
- Texts under other restrictive terms, such as MIT with the Commons Clause, stay
  in the existing snapshots but are never republished in full.
- Removal from git history is not automatic; requests that need it are handled
  case by case and recorded in the issue.
