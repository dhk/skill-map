# skill-doctor

Interactive best-practice reviewer for a single Claude Agent Skill. Give it a
`SKILL.md` — it interviews you about the things the file alone can't reveal
(allowed-tools scoping, data sensitivity, high-stakes actions, triggering, install
scope), then recommends fixes and applies them on your confirmation.

Grounded in the [skill-map](https://github.com/dhk/skill-map) study of ~5,000
crawled skills — corpus findings like ">50% of `Bash` grants are unscoped" and
"~97% of skills omit the anti-trigger" are baked into the rubric.

By [dhk](https://github.com/dhk) — [dhkonskills@dhk.io](mailto:dhkonskills@dhk.io).

---

## Install

### Claude Code (recommended)

In **Claude Code** (the CLI, or the VS Code / JetBrains extension). Run these as
**two separate commands, one at a time**:

```
/plugin marketplace add dhk/skill-map
```

```
/plugin install skill-doctor@skill-map
```

Then invoke it with `/skill-doctor`.

> **Not in Claude Code?** Plugins aren't available in the Claude Desktop app or
> claude.ai. Use the shell install or zip upload below.

### Shell install (works anywhere the CLI is installed)

```bash
curl -fsSL https://raw.githubusercontent.com/dhk/skill-map/main/install.sh | bash
```

Clones the repo and symlinks the skill into `~/.claude/skills`. Then invoke with
`/skill-doctor`.

### claude.ai / Claude Desktop (zip upload)

The chat apps take custom Skills as a zip upload (requires a **Pro, Max, Team, or
Enterprise** plan with **code execution** enabled):

1. Download [`dist/skill-doctor.zip`](dist/skill-doctor.zip) (or rebuild with
   `bash plugins/skill-doctor/build-zip.sh`).
2. Go to **Settings → Features → Skills** and upload `skill-doctor.zip`.

No auto-update — re-upload to get a new version. On claude.ai the "apply edits in
place" step doesn't apply; paste or upload the `SKILL.md` you want reviewed and
Claude returns the improved version.

See [INSTALL.md](INSTALL.md) for a verify-first walkthrough, step-by-step
instructions, and troubleshooting.

---

## What it checks

Five axes, weighted by impact:

| Axis | Weight | Key checks |
|---|---|---|
| Frontmatter | 20% | `name`, `description`, `license`; anti-trigger in description |
| Triggering | 25% | Positive trigger + anti-trigger (`Do NOT use when…`) |
| Progressive disclosure | 15% | Workflow in SKILL.md; details deferred to `reference/` |
| Structure | 15% | `## When to use`, `## When NOT to use`, numbered workflow |
| Safety | 25% | Tool scoping, PHI/PII handling, confirmation before high-stakes actions |

The most common gap across the whole ecosystem: **no anti-trigger** (~97% of
skills omit it). The second most common: **unscoped `Bash` grant** (>50%).

---

## Update / remove

```
/plugin marketplace update skill-map
/plugin uninstall skill-doctor@skill-map
```

---

## What's inside

```
plugins/skill-doctor/
├── .claude-plugin/plugin.json
└── skills/skill-doctor/
    ├── SKILL.md
    └── reference/
        ├── rubric.md
        └── interview-bank.md
```

The skill is self-contained — the rubric is carried as prose in `reference/`, so
it runs anywhere with no Python or network access at runtime.

Version: `1.0.0` — pinned explicitly; you only receive updates when that string
bumps.
