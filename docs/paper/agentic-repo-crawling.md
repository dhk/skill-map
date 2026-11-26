# Research-grade, agent-run repository crawling: gathering, categorising, cleaning and normalising unstructured data from git repositories

Draft 0.1 · 26 November 2026 · Dave Holmes-Kinsella (with Claude as drafting
agent) · Status: first full draft, for review

> **How to read this draft.** Every factual claim about the case study cites a
> file, commit or pull request in this repository. Links are pinned to commit
> SHAs because the four pull requests they come from (#33 to #36) were still
> open when this was written. Statements marked **[inferred]** are the
> author's reading, not something the repository shows. Statements marked
> **[project record]** come from the study's working notes and review threads,
> which are outside the repository. Figures are quoted only where the
> repository's own code, manifests or method notes produce them.

## Abstract

Git repositories are now a primary source for studying how people write
instructions for AI agents, and the files involved (`SKILL.md`, `AGENTS.md`,
plugin manifests) are unstructured, copied freely, dated unreliably and
licensed inconsistently. This paper describes a method for building a
research-grade dataset from such files when most of the engineering is done by
an AI coding agent under human direction. It draws on one study, the Skill
Concepts Atlas in this repository, which imported 3,797,113 `SKILL.md`
occurrences from the GitSkills dataset and built a reference set of 8,168
vendor skill versions in a single working day. We describe the pipeline in
four stages (gather, categorise, clean, normalise), then catalogue thirteen
failures the study met, each with how it was caught. Most were not crawling
problems: they were problems of identity (what counts as the same repository
or text), time (what a date actually bounds), rights (what may be
republished) and provenance (whether a number can be rebuilt). Several were
introduced by the agent and caught by a second agent doing adversarial review
before a human merged anything. We close with a reusable checklist and the
limits of what one study can show.

## 1. Problem

A study of agent skills wants to answer questions such as when an idea first
appeared, how it spread and who wrote it. The raw material makes each of those
hard.

- **Identity is ambiguous.** The same text sits in thousands of repositories:
  GitSkills reports 1,877,981 distinct texts among 3,797,117 files
  ([`gitskills-import.md`](https://github.com/dhk/skill-map/blob/e461e7df58d90a79dece8724c1696fb60a4c25ff/docs/atlas/gitskills-import.md),
  "First run"; [GitSkills](https://arxiv.org/abs/2608.10906)). Repository names are
  case-insensitive on GitHub but not in a dataframe.
- **Dates are claims.** Git author and committer dates can be set freely, and
  bulk publishing resets them. This repository's own lineage trace marks 217
  of 261 copy clusters as date-unreliable
  ([`data/lineage.json`](https://github.com/dhk/skill-map/blob/731bb9d9f26d1f63c76a4767cacf5c519b152f49/data/lineage.json),
  `ancestor_basis_counts`).
- **Rights vary per file.** A repository's licence does not cover a skill
  that declares stricter terms in its own frontmatter
  ([`DATA-POLICY.md`](https://github.com/dhk/skill-map/blob/50675b7823defa50a580bc64b81f3ac3b115b9ce/DATA-POLICY.md),
  rule 4).
- **Authorship is not where it looks.** In `openai/plugins`, 579 of 872 skill
  paths name an author other than OpenAI in their plugin manifest
  ([`docs/atlas/vendor-reference.md`](https://github.com/dhk/skill-map/blob/42d97b4609e5a462e6fcef556f5897f3f9f4a5c3/docs/atlas/vendor-reference.md)).

Agents change the economics. An agent can write an importer, its tests and a
method note in an hour, so the bottleneck moves from writing code to knowing
whether the code's output is true. The method below is organised around that
shift: every stage leaves an artefact a reviewer can check, and nothing is
published or merged on the agent's word.

## 2. The case study

The Skill Map is an existing crawl of 4,975 skills from 43 repositories (June
2026) with a quality rubric
([`docs/STATS.md`](https://github.com/dhk/skill-map/blob/731bb9d9f26d1f63c76a4767cacf5c519b152f49/docs/STATS.md)).
The Skill Concepts Atlas extends it to ask how purposes and concepts in
published Claude and ChatGPT skills spread and change over time
([`docs/atlas/plan.md`](https://github.com/dhk/skill-map/blob/42d97b4609e5a462e6fcef556f5897f3f9f4a5c3/docs/atlas/plan.md)).
The evidence for this paper is the Atlas's first four pull requests, all
opened on 26 November 2026 and stacked on each other:

| PR | Branch head | Delivers |
|---|---|---|
| [#33](https://github.com/dhk/skill-map/pull/33) | `50675b7` | Data policy, ADR 0003, removal list, licence allow-list |
| [#34](https://github.com/dhk/skill-map/pull/34) | `0eba571` | Study plan, ADRs 0004 to 0007 |
| [#35](https://github.com/dhk/skill-map/pull/35) | `e461e7d` | GitSkills importer and its committed manifest |
| [#36](https://github.com/dhk/skill-map/pull/36) | `42d97b4` | Vendor reference set and its committed manifest |

None was merged when this draft was written.

## 3. Pipeline

### 3.1 Gather

**Build on a pinned prior dataset before crawling anything.** File-level
collection of `SKILL.md` at scale had already been done by GitSkills; the
Atlas imports it rather than re-crawling
([ADR 0004](https://github.com/dhk/skill-map/blob/0eba5717c54f6a426f170365fe42784b7f7f555d/docs/adr/0004-atlas-scope-and-corpus.md)).
The importer reads a Hugging Face revision pinned to a full 40-character
commit, refuses any other revision, and checks the dataset card's row counts
(3,797,117 artifacts, 282,200 repositories) before any merging
([`docs/atlas/gitskills-import.md`](https://github.com/dhk/skill-map/blob/e461e7df58d90a79dece8724c1696fb60a4c25ff/docs/atlas/gitskills-import.md),
"Pinning and provenance"). It reads only metadata columns over HTTP range
requests, so the text columns, which stay under their authors' licences, are
never downloaded.

**Make the gather resumable and content-addressed.** Each remote file's
selected columns are cached with the revision, size, hash and column list,
and reused only when all four match (same note, "Resuming").

**Use git itself for histories you need completely.** The vendor reference
set clones each vendor repository without file contents
(`git clone --filter=blob:none`) and lists every `SKILL.md` add, change and
delete with
`git log --first-parent --diff-merges=first-parent --no-renames --raw`, so a
change is dated by the commit that put it on the default branch and unmerged
branches never count
([`docs/atlas/vendor-reference.md`](https://github.com/dhk/skill-map/blob/42d97b4609e5a462e6fcef556f5897f3f9f4a5c3/docs/atlas/vendor-reference.md),
"How a version is found").

**Apply the removal list at ingress, not only at publication.** The crawler
skips excluded repositories and never stores an excluded text, checking both
the blob SHA GitHub reports and one recomputed from the fetched text
([`crawlers/crawl.py` diff in #33](https://github.com/dhk/skill-map/pull/33/files)).
Checking both is a guard against the two disagreeing, for example when the
fetched text was re-encoded **[inferred]**.

**Planned, not yet built:** a delta crawl for August to November 2026 that
reruns GitSkills' size-split code search, so each query stays under GitHub's
result cap, and diffs by blob SHA (plan, "Corpus").

### 3.2 Categorise

**Prefer labels that are facts about the path over labels about the text.**
The platform folder (`.claude`, `.codex`, `.agents` and so on) comes from the
first dot-folder in the path, and the method note says plainly that it is "a
context label, not proof of which agent runs the skill"
([`gitskills-import.md`](https://github.com/dhk/skill-map/blob/e461e7df58d90a79dece8724c1696fb60a4c25ff/docs/atlas/gitskills-import.md),
"Platform folder").

**Record the basis for every inferred label.** Vendor skill authorship is
`first-party`, `other-author` or `unstated`, with an `authorship_basis`
column (`manifest`, `partner_path`, `none`) and the raw `manifest_author`
kept verbatim, so a reader can regroup without trusting the module's
categories (vendor-reference note, "Who wrote it").

**Detect deterministically where you can; use a model only where a rule
cannot decide.** Sophistication is stored as features with a detector
version, and the ladder level is a view computed from them
([ADR 0006](https://github.com/dhk/skill-map/blob/0eba5717c54f6a426f170365fe42784b7f7f555d/docs/adr/0006-atlas-sophistication-ladder.md)).
Concepts are extracted by a model with exact evidence spans, embedded,
clustered and named, then frozen as taxonomy v1
([ADR 0005](https://github.com/dhk/skill-map/blob/0eba5717c54f6a426f170365fe42784b7f7f555d/docs/adr/0005-atlas-concept-method.md)).
Every model-produced row records model, prompt and method versions.

**Validate model labels against a human sample, and report accuracy rather
than gate on it.** ADR 0005 commits to one stratified sample of about 200
skills labelled by the maintainer across every dimension, measuring precision
and recall, plus stability across re-runs and two embedding models. This has
not been run yet (see Limitations). The repository's earlier experience with
an LLM judge (section 4, F10) is the evidence for why it matters.

### 3.3 Clean

**Check keys before writing anything.** The importer stops on any failure of
one representative row per blob SHA, no empty SHAs, unique repo and path per
occurrence, unique repo names, and a repo row for every occurrence
([`gitskills-import.md`](https://github.com/dhk/skill-map/blob/e461e7df58d90a79dece8724c1696fb60a4c25ff/docs/atlas/gitskills-import.md),
"What it does").

**Merge identities by the source system's rules, and log what the merge
loses.** Repository names are merged case-insensitively, with a stated
tie-break rule, and the manifest lists every merge and every text the merge
dropped (F6).

**Remove by content, keep the pointer.** A removed text keeps its row,
repository, path and blob SHA; `skill_md_content` becomes null and
`content_removed` says why. Removal is by blob SHA, so every copy goes,
whichever repository holds it
([`DATA-POLICY.md`](https://github.com/dhk/skill-map/blob/50675b7823defa50a580bc64b81f3ac3b115b9ce/DATA-POLICY.md),
"The removal list"). On 26 November that removed 30 texts from 78 snapshot
rows across 6 repositories.

**Gate republication on both licences.** Full text is published only when the
repository's licence and the skill's own declared licence are both on a
permissive allow-list; excerpts are capped at 300 characters each, 3 per file
and 600 per file in total (`DATA-POLICY.md`, rules 3 and 4;
[`crawlers/licensing.py`](https://github.com/dhk/skill-map/blob/50675b7823defa50a580bc64b81f3ac3b115b9ce/crawlers/licensing.py)).
The GitSkills import publishes a description for 753,797 texts and withholds
it for licence on 1,124,160
([manifest](https://github.com/dhk/skill-map/blob/2c9223654e0d5527d9c88371020fd01cabe9516a/data/atlas/gitskills/manifest.json),
`summary`).

### 3.4 Normalise

**One table per entity, at the lowest grain, keyed by content.** The plan
defines fifteen tables, from `occurrence` (repo, path, blob SHA, SWHID) to
`vendor_match`, each derived row naming its method version (plan, "Data at the
lowest grain"). The git blob SHA is the join key throughout: it is what GitHub
reports, what GitSkills stores, and what Software Heritage indexes.

**Dates are windows, not points.** Each text gets a window from the latest
lower bound (vendor launch, repository creation) to the earliest upper bound
(Software Heritage first-seen, registry first-listed, crawl date). The git
first-commit date is the point estimate only when it falls inside the
window; otherwise the estimate is the upper bound with a low-confidence label
(plan, "Dating"). Every date is published as an estimate.

**Count spread once per near-copy family.** A concept copied into a hundred
catalogues counts once (plan, "Analytical dimensions"; ADR 0005, item 5).

**Every run writes a committed manifest.** The GitSkills manifest records the
method version, resolved revision, every input file with size and SHA-256,
the columns read, the removal list's hash, every identity merge, output row
counts and hashes, and a summary
([manifest](https://github.com/dhk/skill-map/blob/2c9223654e0d5527d9c88371020fd01cabe9516a/data/atlas/gitskills/manifest.json)).
Bulk Parquet goes to release assets and Hugging Face, not git history
([ADR 0007](https://github.com/dhk/skill-map/blob/0eba5717c54f6a426f170365fe42784b7f7f555d/docs/adr/0007-atlas-hosting-and-publication.md)).

## 4. Failure catalogue

Each entry gives what went wrong, how it was caught, its status, and the
general lesson. "Review" means a second agent session doing normal and
adversarial review of a pull request (section 5).

### F1. The project's public claim contradicted its own data

- **What:** the submission form and community seed list told authors that no
  skill content is copied into the repository. The crawl snapshots held
  8,768 non-empty `skill_md_content` rows, 4,341 unique texts from 43
  repositories
  ([ADR 0003](https://github.com/dhk/skill-map/blob/50675b7823defa50a580bc64b81f3ac3b115b9ce/docs/adr/0003-data-redistribution-policy.md)).
- **Caught by:** the agent, while scoping the Atlas's redistribution question
  **[project record]**.
- **Status:** corrected in #33; a removal route and list added.
- **Lesson:** audit what the repository actually stores against what it says
  it stores before adding more data. A policy is a claim about the data and
  needs the same check as any other claim.

### F2. A dataset's licence was misread, twice

- **What:** the first drafts of ADR 0003 and the plan said GitSkills states
  no licence (still visible at
  [`22b6f93`](https://github.com/dhk/skill-map/blob/22b6f93534f7127dd5deba6c9ea034b0413684a8/docs/adr/0004-atlas-scope-and-corpus.md)).
  GitSkills' Hugging Face card releases metadata under CC BY 4.0 with file text
  under origin licences, while its Zenodo record lists CC BY 4.0 for the whole
  record with no split.
- **Caught by:** the agent, corrected across #33 to #35 (#35 description,
  "Correction carried into #33 and #34"); the Zenodo/Hugging Face difference
  by review of #34 (commit
  [`ab4c466`](https://github.com/dhk/skill-map/commit/ab4c46672ea134d30927d727b4a8d6aadb95ac9c)).
- **Status:** ADR 0004 now records both statements and which reading the
  Atlas follows, and why.
- **Lesson:** read every distribution channel's licence statement, record
  disagreements explicitly, and pick the more restrictive reading for text.

### F3. The removal list was not loaded the same way everywhere

- **What:** `crawl.py` and the GitSkills importer load
  `data/exclusions.json` (the importer stops if it is missing and records its
  hash). The vendor reference module does not load it at all
  ([`vendor_reference.py` at `42d97b4`](https://github.com/dhk/skill-map/blob/42d97b4609e5a462e6fcef556f5897f3f9f4a5c3/crawlers/atlas/vendor_reference.py)).
  Nothing changes today because the list's repository section is empty.
- **Caught by:** review of #36 **[project record]**.
- **Status:** open fix on #36.
- **Also:** the older pipeline doc says snapshots are "never mutated"
  ([`incremental-crawl-system.md`](https://github.com/dhk/skill-map/blob/731bb9d9f26d1f63c76a4767cacf5c519b152f49/docs/incremental-crawl-system.md)),
  while removal now edits them in place through `exclusions.py --apply`.
  The data policy reconciles this by having only that script edit snapshots
  and keeping the pointer, but the older document has not been updated
  **[inferred]**.
- **Lesson:** a compliance control is only as strong as its weakest loader.
  Put it in one module, load it at every entry point, record its hash in
  every manifest, and test that each entry point fails without it.

### F4. Archive dates were treated as lower bounds

- **What:** the first plan listed Software Heritage first-seen as "only a
  lower bound"
  ([`22b6f93`](https://github.com/dhk/skill-map/blob/22b6f93534f7127dd5deba6c9ea034b0413684a8/docs/atlas/plan.md)).
  An archive's first-seen date says a file existed by then, so the true first
  publication is on or before it: it is an upper bound. The same holds for
  registry first-listed dates.
- **Caught by:** review of #34; fixed in
  [`ab4c466`](https://github.com/dhk/skill-map/commit/ab4c46672ea134d30927d727b4a8d6aadb95ac9c).
- **Status:** fixed; the dating rule is now a window between bounds.
- **Lesson:** for every date signal, write down which side it bounds before
  using it. Getting this backwards silently shifts every estimate.

### F5. Git dates measure publishing, not writing

- **What:** the June study found per-skill commit count uncorrelated with
  quality (r = −0.002 across 172 skills) and that several large repositories,
  including `anthropics/skills` (89% of skills share one first-commit day),
  were bulk-published snapshots
  ([`llm-judge-tuning.md`](https://github.com/dhk/skill-map/blob/731bb9d9f26d1f63c76a4767cacf5c519b152f49/docs/llm-judge-tuning.md),
  "Does maturity predict quality?"). The lineage trace therefore marks a
  repository as bulk-published when more than half its skills share one
  first-commit day, and treats lineage direction through it as unreliable
  ([`lineage_trace.py`](https://github.com/dhk/skill-map/blob/731bb9d9f26d1f63c76a4767cacf5c519b152f49/crawlers/lineage_trace.py),
  lines 202 to 214).
- **Related:** the vendor reference set's earliest version is dated 15
  October 2025 in `anthropics/skills`, while the plan's floor for `SKILL.md`
  files is the 16 October 2025 announcement (plan, "Dating"). A floor taken
  from an announcement therefore needs a tolerance **[inferred]**.
- **Lesson:** treat git dates as claims inside a window of independent bounds,
  and detect bulk publishing before using dates for direction.

### F6. Case-insensitive repository names broke a key and lost a text

- **What:** GitSkills' repos table has 9 names that differ only by case. They
  break the one-row-per-repo key. After merging, 4 occurrences shared a path
  across two spellings; in one, `lzzmm/gpubk` and `lzzmm/GPUbk` held different
  texts at `src/bk/data/codex-skill/gpubk/SKILL.md`, so one text (`f5b619f2…`)
  could not keep an occurrence and appears nowhere else in the release.
- **Caught by:** the key check on unique repo names failed on the first run
  against the real data (commit message of `300e756`); the agent added the
  merge in
  [`300e756`](https://github.com/dhk/skill-map/commit/300e7569d4aa7190c129bb8563427e050bff29e3).
  The first manifest (method version 1.2.0) produced 1,877,980 distinct texts
  against the card's 1,877,981 but could not say why. The agent added
  `texts_dropped` and per-collision SHAs
  ([`be9cb27`](https://github.com/dhk/skill-map/commit/be9cb27032d2a940f4a95bc0a9588879bc96873e)),
  the maintainer re-ran it (1.2.1,
  [`2c92236`](https://github.com/dhk/skill-map/commit/2c9223654e0d5527d9c88371020fd01cabe9516a)),
  and the gap was explained
  ([`gitskills-import.md`](https://github.com/dhk/skill-map/blob/e461e7df58d90a79dece8724c1696fb60a4c25ff/docs/atlas/gitskills-import.md),
  "First run").
- **Status:** fixed and documented.
- **Lesson:** normalise identifiers by the rules of the system that issued
  them, not by string equality. Reconcile every count against the source's
  published figures, and when they differ by even one, instrument the code
  until the difference is explained.

### F7. Symlinked manifests were read as their link text

- **What:** the vendor module looks for `.claude-plugin/plugin.json` and
  `.codex-plugin/plugin.json` only, although its docstring promises any
  `.<name>-plugin/plugin.json`
  ([`vendor_reference.py` lines 19 to 21 and 179 to 187](https://github.com/dhk/skill-map/blob/42d97b4609e5a462e6fcef556f5897f3f9f4a5c3/crawlers/atlas/vendor_reference.py#L179-L187)).
  In `microsoft/power-platform-skills`, `.claude-plugin/plugin.json` is a
  symlink to `../.plugin/plugin.json`. Git stores a symlink as a blob holding
  the target path, so reading it from a blobless clone returns the path, not
  JSON, and the author comes back empty.
- **Effect:** the review reported 54 versions (11 skills) marked `unstated`
  that name Microsoft. A rebuild for this paper at the same vendor HEADs
  reproduced it: 54 `unstated` version rows in that repository, across 50
  skill paths, have a symlink as their nearest manifest. 11 of those skills
  still read `unstated` in the `skill` table, which takes authorship from the
  last live version; the rest gained a readable manifest later.
- **Caught by:** review of #36 **[project record]**.
- **Status:** open fix on #36.
- **Lesson:** reading files from git objects rather than a checkout bypasses
  the filesystem. Check the tree entry mode (`120000` is a symlink) and
  resolve it, and test against real repositories, not only fixtures.

### F8. Timestamps with offsets were sorted as text

- **What:** the module stores committer dates in strict ISO 8601 with the
  committer's offset (`%cI`) and sorts them as strings
  ([`vendor_reference.py` lines 131, 305 and 330](https://github.com/dhk/skill-map/blob/42d97b4609e5a462e6fcef556f5897f3f9f4a5c3/crawlers/atlas/vendor_reference.py#L305)).
  `2026-01-05T09:00:00-08:00` sorts before `2026-01-05T12:00:00+01:00` as text
  but is six hours later as time. This is the inverse of the usual naive-date
  bug: the dates carry their zones, and the sort throws them away.
- **Effect:** the review reported 6 skills with the wrong first-landed date
  and 38 texts with the wrong first-publishing repository in the copy
  matching, all inside Microsoft, so no headline changed. The rebuild for this
  paper reproduced both figures: 6 skills (4 in
  `anthropics/claude-plugins-official`, 2 in
  `microsoft/power-platform-skills`) and 38 texts whose earliest vendor
  location changes when sorted by instant (37 move from `microsoft/azure-skills`
  to `microsoft/skills`, 1 the other way). The version table holds 14 distinct
  committer offsets.
- **Caught by:** review of #36 **[project record]**.
- **Status:** open fix on #36: sort by UTC instant, or by git's own order.
- **Lesson:** convert to UTC instants at ingestion and sort on those. When
  order within one branch matters, the commit graph's order is more reliable
  than any timestamp.

### F9. A published number came from no committed code

- **What:** the vendor reference note reports 24 vendor-to-vendor copies of 23
  texts. The review reproduced the figures with its own script but found no
  code or manifest field in the repository that produces them
  **[project record]**. The vendor manifest's summary has no such field
  ([manifest at `c1f18e2`](https://github.com/dhk/skill-map/blob/c1f18e2dc4752b1e236fc25225859551e2d94484/data/atlas/vendor_reference/manifest.json)).
- **Status:** open fix on #36.
- **Lesson:** every number in prose must be emitted by committed code into a
  committed manifest. An agent can compute a correct number in a scratch
  session and write it into a document; the number is then true but not
  reproducible.

### F10. An LLM judge measured its own harness

- **What:** the June LLM judge rated `anthropics/skills` and `openai/skills`
  "weak". Two causes were harness bugs: every skill was cut to 6,000
  characters (47% of `xlsx`, 66% of `figma-use`), and the judge never saw the
  sibling `references/` and `scripts/` folders it then criticised the skills
  for lacking. The third was an uncalibrated scale with no anchor
  ([`llm-judge-tuning.md`](https://github.com/dhk/skill-map/blob/731bb9d9f26d1f63c76a4767cacf5c519b152f49/docs/llm-judge-tuning.md)).
- **Caught by:** the result was implausible for known-good skills.
- **Status:** fixed in `judge_llm.py` (full text up to 32k characters, sibling
  listing injected, per-axis anchored scores); a targeted re-judge moved all
  four test skills out of "weak".
- **Lesson:** include known-good and known-bad items in every labelling run,
  give the model everything a human labeller would see, and treat implausible
  verdicts on anchors as harness bugs first.

### F11. A short revision id is not a pin

- **What:** the importer first pinned GitSkills to the short id `ebab174`
  shown on the dataset page. A short id can become ambiguous and does not by
  itself prove which commit was read.
- **Caught by:** review of #35; the full commit could only be resolved once
  the network allowed it, on the first real run (#35 description; `be9cb27`).
- **Status:** fixed: `sources.json` records the full SHA and how it was
  resolved, and the importer refuses anything else.
- **Lesson:** pin to full content hashes, record how each pin was obtained,
  and check expected row counts as a second guard.

### F12. The agent could not reach the data, so the human ran it

- **What:** the agent's sandbox proxy refused huggingface.co and zenodo.org,
  so #35 first shipped "not yet run against the real data" (#35 description).
  The maintainer ran the importer, and later the vendor `mirror` join (the
  vendor note documents a `uv run` invocation), on their own machine, and
  committed the manifests
  ([`2c92236`](https://github.com/dhk/skill-map/commit/2c9223654e0d5527d9c88371020fd01cabe9516a),
  [`c1f18e2`](https://github.com/dhk/skill-map/commit/c1f18e2dc4752b1e236fc25225859551e2d94484);
  both commits carry a −08:00 offset, unlike the agent's).
- **What it means for provenance:**
  - The manifests record data inputs and outputs by hash, but not the
    interpreter, library versions or host. The vendor manifest's version and
    skill tables have the same row counts and the same vendor repository HEADs
    in the agent's run (`4652f88`) and the maintainer's (`c1f18e2`), yet
    different SHA-256 hashes. A different Parquet writer version is a likely
    cause **[inferred]**; the manifest cannot say. The rebuild for this paper,
    on Linux with pyarrow 26.0.1, reproduced the agent's hashes exactly, so
    the code is deterministic on one toolchain and the difference arises
    between hosts.
  - Two maintainer runs produced two manifests from different code: method
    version 1.2.0 (`28e8392`) and 1.2.1 (`2c92236`). When the agent asked for
    the re-run, the maintainer's checkout was behind the branch
    **[project record]**. The `method_version` field is what distinguishes
    them; the manifest does not record the code commit itself.
- **Lesson:** when execution moves between machines, record the toolchain in
  the manifest, hash a canonical form of each table (sorted rows, fixed
  schema) as well as the file, and record the code commit that produced the
  run.

### F13. Prose drifted from the counted unit

- **What:** "21 partner skills" in the #36 description and note are 21 copies
  across 19 skill paths **[project record: review of #36]**. The plan says
  GitSkills has commit dates "for 458,548 files (about 24% of 1,877,981
  distinct texts)", dividing a file count by a text count; the import
  manifest's own count is 458,136 distinct texts with commit history
  (`contents_with_commit_history`), which is also 24%
  ([manifest](https://github.com/dhk/skill-map/blob/2c9223654e0d5527d9c88371020fd01cabe9516a/data/atlas/gitskills/manifest.json)).
- **Status:** the first is an open fix on #36; the second is noted here.
- **Lesson:** every number names its unit (occurrence, distinct text, skill
  path, repository), and prose quotes the manifest field it came from.

## 5. The agent workflow

The work was done by agent sessions under one human maintainer. What follows
is how the work was organised, with the evidence for each part.

- **Thread per task.** Each unit of work (data policy, plan, importer, vendor
  set, and this paper) ran in its own agent session with a written brief
  **[project record]**.
- **Stacked pull requests, one decision each.** #34 depends on #33, #35 is
  stacked on #34 and #36 on #35, and each says so in its description. The
  agent authored the code commits; the maintainer authored the commits that
  ran against real data (`git log` on each branch).
- **Companion adversarial review.** Each pull request got a second agent
  session doing a normal and an adversarial review, without push access,
  reporting to the maintainer rather than commenting on GitHub
  **[project record]**. F2, F3, F4, F7, F8, F9, F11 and F13 came from those
  reviews. The #36 review rebuilt the vendor tables from scratch and got
  byte-identical output to the author's run **[project record]**; a third
  rebuild for this paper, from fresh clones at the same HEADs, matched the
  committed hashes at `4652f88` too.
- **Clear fixes versus decisions.** Review findings were split into clear
  fixes, applied without discussion, and decisions for the maintainer. The
  maintainer approved twenty decisions at once, and each pull request lists
  them under "Review decisions applied (approved 26 Nov 2026)" (#33 to #35
  descriptions).
- **Human merge gate.** No agent merges. All four pull requests were open at
  the time of writing.
- **Cost gate before large model runs.** Concept extraction runs on a
  50,000-skill sample first and reports cost and accuracy; the full run waits
  for the maintainer's go-ahead
  ([ADR 0005](https://github.com/dhk/skill-map/blob/0eba5717c54f6a426f170365fe42784b7f7f555d/docs/adr/0005-atlas-concept-method.md),
  item 1). Not yet exercised.
- **Public steps wait.** Publishing to Hugging Face, Zenodo and dhk.io waits
  for the maintainer (ADR 0007, "Consequences").
- **CI as a backstop, not a judge.** The existing Corpus Guard posts a
  doc-drift check and a contributor-vetting check on every pull request,
  advisory only
  ([`corpus-guard.yml`](https://github.com/dhk/skill-map/blob/731bb9d9f26d1f63c76a4767cacf5c519b152f49/.github/workflows/corpus-guard.yml)).
  No CI job runs the Atlas tests yet **[project record: review of #35]**.

What this arrangement bought, in this study: the author agent introduced F4,
F7, F8, F9 and F11, and a separate agent caught them before merge. The
pattern is the familiar one of separating author and reviewer; agents make
it cheap enough to apply to every pull request. What it did not catch is
equally telling: F12's hash drift and F13's unit mixing in the plan were
found while writing this paper, not by review.

## 6. Checklist

**Before gathering**

- [ ] Audit what the repository already stores against what it says it stores (F1).
- [ ] Read the licence on every channel a dataset is distributed through; record disagreements and the reading you follow (F2).
- [ ] Look for a prior dataset and import it pinned to a full hash, with expected row counts (F11).
- [ ] Write the removal list and load it from one module at every entry point; fail closed when it is missing (F3).

**While gathering and categorising**

- [ ] Key everything by content hash; keep the pointer (repo, path, blob SHA, SWHID) even when the text goes.
- [ ] Normalise identifiers by the issuing system's rules (case, renames, forks) and log every merge and what it lost (F6).
- [ ] Resolve symlinks and check tree modes when reading from git objects (F7).
- [ ] Store a basis column next to every inferred label, and keep raw values verbatim.
- [ ] Give a model labeller everything a human would see; include known-good and known-bad anchors (F10).

**Dating**

- [ ] For each date signal, write down which side it bounds (F4).
- [ ] Convert to UTC instants at ingestion; sort by instant or by commit order, never by string (F8).
- [ ] Detect bulk publishing before using git dates for direction (F5).
- [ ] Publish dates as windows with a confidence level; apply floors with a tolerance.

**Reproducibility**

- [ ] Every published number is emitted by committed code into a committed manifest field (F9).
- [ ] Every number names its unit (F13).
- [ ] Reconcile counts against the source's published figures; explain any difference (F6).
- [ ] Record method version, code commit, toolchain and host in the manifest; hash a canonical form of each table (F12).

**Agent workflow**

- [ ] One task per agent session, one pull request per decision.
- [ ] A second agent reviews every pull request adversarially and rebuilds its outputs.
- [ ] Split findings into clear fixes and human decisions.
- [ ] A human merges; a cost estimate precedes any large model run; public steps wait for a human.

## 7. Limitations

- **One study, one day.** All four pull requests were written and reviewed on
  26 November 2026 and none had merged. Failure rates and the share caught by
  review are not estimates of anything general.
- **Labelling is planned, not shown.** The concept extraction, the 50,000-skill
  sample and the 200-skill hand check have not run. The evidence for LLM
  labelling here is the June judge post-mortem, which used a targeted
  re-judge of four skills, not a hand-labelled sample.
- **Software Heritage and the delta crawl are not built.** The dating window
  and the size-split search are designs. Their failure modes are unobserved.
- **Some evidence is outside the repository.** Review findings for F3, F7, F8,
  F9 and F13, and the workflow details marked **[project record]**, come from
  the study's working notes and review threads. Until the #36 fixes land, the
  repository shows the bugs but not the reviewer's counts.
- **Author and subject overlap.** This draft was written by an agent of the
  same kind that did the work it describes. A human or independent review of
  the paper itself is still needed.

## References

- Destefanis, G., Graziotin, D., Vaccargiu, M. and Ortu, M. GitSkills: A
  Dataset of Agent Skills on GitHub. [arXiv:2608.10906](https://arxiv.org/abs/2608.10906);
  Zenodo [10.5281/zenodo.21875637](https://doi.org/10.5281/zenodo.21875637),
  version 1.0.0.
- Prior work on the skill ecosystem cited by the study plan (Skill
  Constellations, How Agent Skills Evolve, From Anatomy to Smells, Ling et al.,
  What Keeps Skills from Being Reusable?) is listed with links in
  [`docs/atlas/plan.md`](https://github.com/dhk/skill-map/blob/42d97b4609e5a462e6fcef556f5897f3f9f4a5c3/docs/atlas/plan.md).
- Anthropic, [Introducing Agent Skills](https://www.anthropic.com/news/skills),
  16 October 2025 (the plan's `SKILL.md` floor).
- Software Heritage, content identifiers (SWHID), [docs.softwareheritage.org](https://docs.softwareheritage.org/devel/swh-model/persistent-identifiers.html).
