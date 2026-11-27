# Method note: the vendor reference set

Date: 2026-11-26 · Code: [`crawlers/atlas/vendor_reference.py`](../../crawlers/atlas/vendor_reference.py)
· Repositories: [`crawlers/atlas/vendors.json`](../../crawlers/atlas/vendors.json)

## What it is for

The [plan](plan.md) classifies vendor repackaging (verbatim mirror, light edit,
derivative, independent) against "every historical version of vendor skills".
This is that reference: every `SKILL.md` version that 9 vendors published from
20 repositories, as git blob SHAs, with when it landed and who the vendor says
wrote it. An exact copy in the wild has the same blob SHA as a vendor version,
so mirrors can be found by a join; edits and derivatives need the similarity
step that comes later.

## First run (26 Nov 2026)

| | Count |
|---|---|
| SKILL.md adds, changes and deletes on default branches | 8,168 |
| Distinct texts (blob SHAs) | 5,111 |
| Skill paths ever published | 2,709 |
| Skill paths still present today | 1,518 |
| Earliest version | 15 Oct 2025 (`anthropics/skills`) |
| Texts shipped identically by more than one vendor | 23 (24 vendor-to-vendor copies, 22 skills) |

| Vendor | Skill paths | Present today | First-party | Other author | Unstated |
|---|---|---|---|---|---|
| Microsoft | 1,057 | 500 | 473 | 10 | 574 |
| OpenAI | 1,020 | 585 | 342 | 611 | 67 |
| Anthropic | 426 | 338 | 278 | 81 | 67 |
| Sentry | 61 | 31 | 60 | 0 | 1 |
| Hugging Face | 56 | 20 | 48 | 0 | 8 |
| Vercel | 43 | 14 | 0 | 0 | 43 |
| Cloudflare | 34 | 24 | 32 | 0 | 2 |
| Google | 7 | 4 | 5 | 0 | 2 |
| Supabase | 5 | 2 | 0 | 0 | 5 |

Matched against the GitSkills occurrence table (run on 26 Nov 2026, GitSkills
commit `ebab1745`): **74,596 occurrences in 9,699 repositories are
byte-identical to a vendor version**, covering 2,445 of the 5,111 vendor texts
(48%). That is 2.0% of GitSkills' 3,797,113 occurrences and 3.4% of its
282,191 repositories. Only exact copies count here; edited copies need the
similarity step. Vendor versions published after the GitSkills crawl cannot
have copies in it, so the 48% understates how much of the recent vendor output
gets copied.

Each repository's HEAD at the time of the run is pinned in
[`data/atlas/vendor_reference/manifest.json`](../../data/atlas/vendor_reference/manifest.json).

Three findings already matter for the repackaging work. The copy numbers come
from the `cross_vendor` table and the `cross_vendor` section of the manifest.

- **Shipped by is not written by.** In `openai/plugins`, 579 of 872 skill
  paths have a plugin manifest naming an author other than OpenAI (Twilio,
  Vercel Labs, Zoom, Shopify and others); 286 name OpenAI.
- **Vendors copy each other.** A text one vendor published first later
  appeared byte-for-byte at another vendor 24 times, in 22 skills. 21 of those
  copies, in 19 skills, are in `openai/plugins`: Hugging Face 8 copies in 8
  skills, Cloudflare 6 in 6, Supabase 5 in 3 (its `supabase` skill in 3
  versions) and Vercel 2 in 2. 7 of the 8 Hugging Face copies landed the same
  day in both places, so the dates do not settle their direction. The other 3
  are Anthropic's `skill-creator` and `mcp-builder`, copied unchanged into
  `microsoft/skills` (both) and `supabase/agent-skills` (`skill-creator`)
  about two months after Anthropic published them.
- **A manifest can name the copier.** 4 of those copies sit in OpenAI plugins
  whose manifest names OpenAI as author (`agents-sdk`, first published by
  Cloudflare; `deploy-to-vercel` and `web-design-guidelines`, by Vercel;
  `supabase-best-practices`, by Supabase). The `authorship` column reports
  what the manifest says, so those 4 read `first-party`; the `cross_vendor`,
  `mirror` and later `vendor_match` steps, which go by text and date, are what
  catch them.

Dates are when each text landed on the vendor's default branch, from the
`version` table.

## How a version is found

- Each repository is cloned without file contents (`git clone --filter=blob:none`),
  so history and paths are complete and only small manifests are fetched.
- `git log --first-parent --diff-merges=first-parent --no-renames --raw` over
  `*SKILL.md` on the default branch lists every add, change and delete in the
  order it landed. A change made on a branch is dated by the commit that put
  it on the default branch (for a merged pull request, the merge), because
  that is when the vendor published it. Unmerged branches never count.
- Renames are recorded as a delete and an add with the same blob SHA, so a
  moved skill keeps its text identity.
- Only files named exactly `SKILL.md` count, matching GitSkills.
- All dates are stored in UTC (`2026-03-01T15:00:00Z`), so they compare
  correctly across time zones; when two versions land in the same second,
  git's landing order decides which came first.

## Who wrote it

The author comes from the nearest plugin manifest above the skill: a
`plugin.json` inside any `.<name>-plugin/` or `.plugin/` folder
(`.claude-plugin`, `.codex-plugin` and `.cursor-plugin` are preferred, in
that order, when a folder has several). It is read at the commit that added or
changed the skill; a deleted skill is read as it stood just before the delete.
A manifest that is a symlink inside the repository is followed, as in
`microsoft/power-platform-skills`, where `.claude-plugin/plugin.json` links to
a shared `.plugin/plugin.json`.

| `authorship` | Means | `authorship_basis` |
|---|---|---|
| `first-party` | the manifest's author contains one of the vendor's names | `manifest` |
| `other-author` | the manifest names someone else, or there is no author and the path is one the repository sets aside for partners (`external_plugins/`, `partner-built/`) | `manifest` or `partner_path` |
| `unstated` | no manifest author and no partner path | `none` |

`manifest_author` keeps the name exactly as written. "Other author" is
deliberately broad: it includes partner companies, but also team names such as
"Data Analytics Maintainers" in `openai/role-specific-plugins` and a few named
individuals, who may well be the vendor's own staff. The module does not guess;
a reader who wants a tighter split can regroup on `manifest_author`. Template
placeholders ("Your Name") count as no author.

## Tables

All Parquet, kept out of git like the other Atlas tables
([ADR 0007](../adr/0007-atlas-hosting-and-publication.md)); the manifest with
row counts and output hashes is committed.

| Table | Grain | Main fields |
|---|---|---|
| `version` | one SKILL.md add, change or delete | vendor, repo, repo licence, path, skill directory, commit, committed and authored dates (UTC), change, blob SHA, previous blob SHA, plugin manifest, manifest author, authorship and basis, whether the text is on the removal list |
| `cross_vendor` | one vendor that published, byte for byte, a text another vendor published first | blob SHA, origin vendor, repo, path and landing date, copy vendor, repo, path and landing date, the copy's manifest author and authorship, same-day flag |
| `skill` | one repository and path | first landed, last changed, distinct versions, present today, current blob SHA, authorship of its last live version |
| `mirror` | one GitSkills occurrence outside the vendor repositories whose text is byte-identical to a vendor version | blob SHA, vendor, vendor repo and path it is credited to, when that path first published it, that path's authorship and manifest author, credit (`vendor` or `repackaged`), copy repo, copy path, platform folder |

Every row carries `method_version`; every table's metadata carries the CC BY
4.0 attribution.

## The removal list

The removal list ([`data/exclusions.json`](../../data/exclusions.json)) is
loaded exactly as the GitSkills importer loads it, and the manifest records
its hash. A vendor repository on it is skipped, and copies in repositories on
it are left out of `mirror`. A vendor text on it keeps its pointer, since no
text is published, with `removal_listed` set. On the first run that is 24
versions: Anthropic's `docx`, `pdf`, `pptx` and `xlsx` skills, whose own
front matter declares a proprietary licence.

## What it leaves out, and why

- **Skill text.** None is copied; rows are pointers into public repositories.
  The repository licence is recorded as metadata only. Several vendor
  repositories have no repository licence (`anthropics/skills`, `openai/skills`,
  `openai/plugins`, `vercel-labs/agent-skills`), and some skills carry their
  own licence files, so any later step that shows vendor text has to check
  per skill.
- **Community marketplaces.** `anthropics/claude-plugins-community` and
  `openai/community-plugins` list third-party work, so they are not vendor
  publications.
- **Vendors not yet listed.** The list is what a search of vendor GitHub
  organisations found on 26 Nov 2026. Adding a repository is a one-line change
  to `vendors.json`.

## Running it

```
uv run --with pyarrow python -m crawlers.atlas.vendor_reference
```

The first run clones into `data/atlas/.cache/vendor-clones/` (ignored by git)
and takes a few minutes; later runs fetch only what changed. `--offline`
reuses the clones as they are.

The `mirror` table needs the GitSkills import output, which lives where the
import ran:

```
uv run --with pyarrow python -m crawlers.atlas.vendor_reference --gitskills data/atlas/gitskills
```

That adds `mirror.parquet` and a `mirror` summary to the manifest (copies,
copying repositories, vendor texts copied, copies by credit, the credit rule and
the GitSkills revision used). Each text is credited to the earliest path where
a vendor published it as its own (first-party or unstated); only a text no
vendor published as its own goes to the earliest path naming another author,
with credit `repackaged` ([copy-flow.md](copy-flow.md#what-counts)).
