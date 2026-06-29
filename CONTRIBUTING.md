# Contributing

Two ways to take part: **submit your skills repo** to the map, and **audit your
skills** against the ecosystem.

## Submit your skills repo

The [skill map](https://dhk.github.io/skill-map/) indexes repos **by reference** —
the crawler reads your public `SKILL.md` files where they live. We don't copy your
skills here; they stay in your repo and you keep ownership.

Pick whichever is easier:

### Option A — issue form (no git needed)
Open a [**Submit a skill repo**](https://github.com/dhk/skill-map/issues/new?template=submit-skill.yml)
issue and fill in your `owner/repo`. We'll add it to the community list and it'll
appear after the next crawl.

### Option B — pull request
Add a row to [`crawlers/crawl-lists/community.md`](crawlers/crawl-lists/community.md):

```markdown
| owner/repo | single-skill | One-line description of what it does. |
```

Only the `repo` column is required by the crawler; the rest is human context.

**Requirements:** the repo is public and has at least one `SKILL.md`.

## Audit your skills

Before (or instead of) submitting, grade your skills against the Anthropic gold
standard and the crawled corpus.

**Locally:**
```bash
pip install pyyaml
python crawlers/audit_repo.py /path/to/your/skills          # local
python crawlers/audit_repo.py --github owner/repo            # any public repo
python crawlers/audit_repo.py --github owner/repo --token "$GITHUB_TOKEN"  # private
```

**As a GitHub Action** (auto-comments the report on every PR that touches a
`SKILL.md`) — see [`.github/actions/skill-audit`](.github/actions/skill-audit/README.md):
```yaml
- uses: dhk/skill-map/.github/actions/skill-audit@main
```

**Improve one skill interactively:** use the
[`skill-doctor`](plugins/skill-doctor/skills/skill-doctor/SKILL.md) skill — it
interviews you about allowed-tools scoping, data sensitivity (PHI/PII),
high-stakes actions, triggering, and install scope, then recommends and applies
fixes. Install it from this repo's marketplace:

```
/plugin marketplace add dhk/skill-map
/plugin install skill-doctor@skill-map
```

The auditor reports your repo's signature, a benchmark vs. same-type peers, your
worst offenders, overlapping skills to consolidate, and the top general-purpose
skills you're missing. The most common gap across the whole ecosystem is the
**anti-trigger** (`Do NOT use when…`) — ~97% of skills omit it, and it's the
cheapest win.

## How the data flows

```
your repo (SKILL.md)  →  community.md (a reference)  →  crawler  →  scorer  →  map + studies
```

The crawl stores immutable snapshots under `crawlers/crawls/`; `run_pipeline.py`
recomputes every derived finding from them. See
[docs/incremental-crawl-system.md](docs/incremental-crawl-system.md).
