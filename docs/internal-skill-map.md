# Internal Skill Map — Design Doc

**The idea:** point the skill map crawler at a corporate GitHub org and automatically discover, classify, and visualize all Claude Code skills living there — the same force-directed map, but for your team's internal skill corpus.

---

## What the crawler is looking for

A Claude Code skill is any GitHub repository (or directory within a monorepo) that matches one or more of these signals:

| Signal | Path | What it means |
|--------|------|---------------|
| Skill entrypoint | `.claude/skills/<name>/` | The canonical skill location |
| Project instructions | `CLAUDE.md` at root | Project-level Claude context — may describe what the skill does |
| Skill manifest | `.claude/skills/<name>/README.md` | Human-readable skill description |
| Hooks config | `.claude/settings.json` | Presence confirms Claude Code integration |
| Slash commands | `.claude/commands/*.md` | Custom commands shipped with the skill |

A repo that has any of `.claude/`, `CLAUDE.md`, or `*.skill` files is a candidate. A repo with a `.claude/skills/` subtree is a confirmed skill host.

---

## Architecture

```
GitHub Org
    │
    ▼
[Crawler]  ── GitHub API ──▶ repo list → file tree scan → CLAUDE.md parse
    │
    ▼
[Classifier]  ── keyword match on descriptions → domain assignment
    │
    ▼
[Graph Builder]  ── same data model as public map → nodes + links JSON
    │
    ▼
[Exporter]  ── splice JSON into index.html → single-file deployment
    │
    ▼
[Target]  ── GitHub Pages / S3 / internal wiki embed
```

---

## Phase 1 — Crawl

### Auth

For most corporate setups, a **Personal Access Token** with `read:org` + `repo` (or `read:org` + `contents:read` for fine-grained tokens) is the fastest path.

For team/enterprise use, a **GitHub App** is better: scoped per-installation, auditable, no individual credential dependency. Needs `Repository contents: Read` and `Organization members: Read`.

```bash
# Quickest local test
export GH_TOKEN=ghp_...
gh api orgs/YOUR_ORG/repos --paginate | jq '.[].name'
```

### Repo scan

```python
import requests, os

ORG = "your-org"
TOKEN = os.environ["GH_TOKEN"]
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}

def list_repos(org):
    repos, page = [], 1
    while True:
        r = requests.get(f"https://api.github.com/orgs/{org}/repos",
                         headers=HEADERS, params={"per_page": 100, "page": page})
        batch = r.json()
        if not batch: break
        repos.extend(batch)
        page += 1
    return repos

def is_skill_repo(owner, repo):
    """Returns True if repo contains Claude Code skill signals."""
    for path in [".claude", "CLAUDE.md", ".claude/skills"]:
        r = requests.get(f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                         headers=HEADERS)
        if r.status_code == 200:
            return True
    return False
```

**Rate limit note:** GitHub allows 5,000 requests/hour for authenticated tokens. At 2 API calls per repo, a 500-repo org costs ~1,000 requests. Fine for a nightly cron; add caching for anything more frequent.

### Skill extraction

For each confirmed skill repo, extract:

```python
def extract_skill_metadata(owner, repo):
    meta = {"id": f"{owner}/{repo}", "org": owner, "label": repo}

    # Try CLAUDE.md first
    r = requests.get(f"https://api.github.com/repos/{owner}/{repo}/contents/CLAUDE.md",
                     headers=HEADERS)
    if r.status_code == 200:
        import base64
        content = base64.b64decode(r.json()["content"]).decode()
        meta["description"] = extract_first_paragraph(content)

    # Fall back to README.md
    elif ...:
        ...

    return meta
```

`extract_first_paragraph` strips the H1, finds the first non-empty paragraph. Good enough for a description without running an LLM.

---

## Phase 2 — Classify

The public map uses 13 manually curated domains. For an internal map, you have two options:

### Option A: Map to the same 13 domains
Use keyword matching on skill name + description:

```python
DOMAIN_KEYWORDS = {
    "Developer Tools":        ["sdk", "api", "cli", "scaffold", "codegen"],
    "Security & Auth":        ["auth", "security", "secret", "vulnerability", "audit"],
    "Data & Databases":       ["sql", "dbt", "database", "query", "schema", "pipeline"],
    "Testing & Debugging":    ["test", "debug", "qa", "playwright", "coverage"],
    "DevOps & Infrastructure":["terraform", "deploy", "ci", "cd", "docker", "k8s"],
    "Agent Orchestration":    ["agent", "mcp", "orchestrat", "workflow", "subagent"],
    "Session Layer":          ["log", "plan", "context", "day", "weekly", "briefing"],
    # ... etc
}

def classify(name, description):
    text = (name + " " + description).lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(k in text for k in keywords):
            return domain
    return "Other"
```

### Option B: Derive domains from repo topics
GitHub repo topics are team-curated — `gh repo edit --add-topic claude-skill,data` — and more accurate than keyword matching. Use them directly as domain labels.

```python
def get_domain_from_topics(repo_data):
    topics = repo_data.get("topics", [])
    # strip 'claude-skill' tag, use remaining as domain hint
    domain_topics = [t for t in topics if t != "claude-skill"]
    return domain_topics[0].replace("-", " ").title() if domain_topics else "Other"
```

---

## Phase 3 — Build the graph

Same data model as the public map. The graph JSON has two arrays:

```json
{
  "nodes": [
    {"id": "domain:Data & Databases", "type": "domain", "label": "Data & Databases", "count": 12},
    {"id": "org:data-team",           "type": "org",    "label": "data-team", "count": 5},
    {"id": "data-team/sql-review",    "type": "skill",  "label": "sql-review",
     "org": "data-team", "domain": "Data & Databases", "description": "..."}
  ],
  "links": [
    {"source": "domain:Data & Databases", "target": "data-team/sql-review", "type": "domain"},
    {"source": "org:data-team",           "target": "data-team/sql-review", "type": "org"}
  ]
}
```

The existing `index.html` consumes this structure exactly. No changes to the visualisation layer needed.

---

## Phase 4 — Export

The public map's `exportSeededPage()` function splices JSON into the HTML at two sentinel constants:

```js
const SEED_DATA = null;      // ← replaced with graph JSON on export
const PASSWORD_HASH = '';    // ← optional SHA-256 password gate
```

For the internal map, do this at build time in Python:

```python
def build_html(graph_data, password=None):
    with open("index.html") as f:
        html = f.read()

    import json
    html = html.replace("const SEED_DATA = null;",
                         f"const SEED_DATA = {json.dumps(graph_data)};")

    if password:
        import hashlib
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        html = html.replace("const PASSWORD_HASH = '';",
                             f"const PASSWORD_HASH = '{pw_hash}';")

    with open("dist/index.html", "w") as f:
        f.write(html)
```

---

## Deployment options

| Target | How | Auth |
|--------|-----|------|
| GitHub Pages (org) | Push `dist/index.html` to a `gh-pages` branch in a dedicated repo | GitHub SSO if org enforces it |
| Internal wiki | Embed as an iframe or paste raw HTML | Same as wiki auth |
| S3 + CloudFront | Upload `dist/index.html`, set index document | IAM / Cognito |
| Vercel / Netlify | Connect repo, set build output to `dist/` | Team auth |
| Password-gated (no infra) | Use the built-in `PASSWORD_HASH` gate | SHA-256, no server |

For most teams, **GitHub Pages on a private org repo** is the zero-infra path. GitHub Pages supports private repos on Team/Enterprise plans, and SSO handles access.

---

## Automation

Run the full pipeline on a schedule (nightly is usually enough — skill repos don't change by the minute):

```yaml
# .github/workflows/skill-map.yml
name: Rebuild skill map
on:
  schedule:
    - cron: '0 6 * * *'   # 06:00 UTC daily
  workflow_dispatch:        # also triggerable manually

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install requests
      - run: python crawler.py --org ${{ vars.TARGET_ORG }} --out graph_data.json
        env:
          GH_TOKEN: ${{ secrets.SKILL_MAP_TOKEN }}
      - run: python build.py --graph graph_data.json --out dist/index.html
      - uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./dist
```

---

## What's different from the public map

| Public map | Internal map |
|-----------|-------------|
| Static data (crawled once) | Rebuilt nightly from live org state |
| 52 orgs, manually curated | Your org's actual teams |
| 1,119 skills, public corpus | Whatever your org has built |
| Personas are archetypal | Personas could map to your actual teams |
| No auth (public) | Password gate or SSO |
| No install path (no registry) | `git clone` from your internal GitHub works directly |

The **session layer gap still exists internally** — most corporate skill corpora mirror the public pattern: task-layer skills, nothing for continuity or rhythm. The internal map will show that immediately, the same way the public map does.

---

## Open questions before building

1. **Monorepo vs multi-repo:** Does your org put skills in one repo under `.claude/skills/*/` or one repo per skill? The crawler handles both but the detection logic differs.
2. **Taxonomy:** Use the 13 public domains, derive from repo topics, or define your own?
3. **Sensitive skill content:** Some CLAUDE.md files may contain internal process details. Scrub descriptions before publishing, or keep the map internal-only.
4. **Contribution tracking:** Do you want the graph to show which team owns which skill (by GitHub team, not just org)? Requires the Teams API.
5. **Freshness indicator:** Add a "last seen" timestamp per skill node — skills that haven't been touched in 12+ months may be stale.
