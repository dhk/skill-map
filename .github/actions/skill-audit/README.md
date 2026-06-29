# Skill Audit — GitHub Action

Grade your [Claude Agent Skills](https://docs.claude.com/en/docs/claude-code/skills)
against the Anthropic gold standard and the crawled ecosystem corpus, and get the
report as a **pull-request comment** — automatically, on every PR that touches a
`SKILL.md`.

It's the [`audit_repo.py`](../../../crawlers/audit_repo.py) auditor behind the
[skill map](https://dhk.github.io/skill-map/), wrapped so you never have to clone
anything.

## What you get

A comment (updated in place, not re-posted) with:

- **Your repo's signature** (boutique, mega-collection, domain-pack…) and a
  benchmark against same-signature peers in the corpus.
- **Grade distribution** + **median quality** (0–100).
- **"Fix these first"** — the most common issues across your skills. The
  near-universal one is **`no-anti-trigger`**: ~97% of all skills in the
  ecosystem never say when *not* to fire. Adding `Do NOT use when…` to a
  description is the single cheapest quality win.
- **Worst offenders**, **overlapping skills to consolidate**, and the **top
  general-purpose skills you're missing** (widely adopted + high quality
  elsewhere).

## Quick start

Drop this in `.github/workflows/skill-audit.yml`:

```yaml
name: Skill Audit
on:
  pull_request:
    paths: ['**/SKILL.md', '.claude/skills/**']
permissions:
  contents: read
  pull-requests: write
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dhk/skill-map/.github/actions/skill-audit@main
```

That's it. Open a PR that adds or edits a skill and the report shows up.

## Inputs

| Input | Default | Description |
|---|---|---|
| `path` | `.` | Directory to scan for `SKILL.md` files. |
| `token` | `github.token` | Token used to post the comment / read private repos. |
| `skill-map-ref` | `main` | Pin the scorer + corpus to a ref for reproducibility. |
| `comment` | `true` | Post/update the PR comment. |
| `fail-under` | `0` | Fail the check if median quality is below this (0 = advisory only). |

### Turn it into a gate

Advisory by default. To **block** PRs that drop below a bar:

```yaml
      - uses: dhk/skill-map/.github/actions/skill-audit@main
        with:
          fail-under: 70
```

## Outputs

`median-quality`, `signature`, `report-path` — wire them into later steps (badges,
status checks, Slack notifications…).

## Run it locally

No Action needed for a one-off:

```bash
git clone https://github.com/dhk/skill-map
pip install pyyaml
python skill-map/crawlers/audit_repo.py /path/to/your/skills
python skill-map/crawlers/audit_repo.py --github you/private-repo --token "$GITHUB_TOKEN"
```
