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

### One-shot, repo-free (recommended)

```bash
pipx run dhk-skill-doctor
```

No git, no clone of this repo — the skill content ships as data inside the
PyPI wheel, so `pipx` fetches it, runs the installer once in a throwaway venv,
and leaves nothing behind but the skill itself at `~/.claude/skills/skill-doctor`.
Then invoke it with `/skill-doctor`.

Re-run the same command any time to update (or add `--force` if you've since
edited the installed copy by hand and want to reset it).

> No `pipx`? `pip install pipx && pipx ensurepath`, or see the
> [pipx docs](https://pipx.pypa.io/stable/installation/).

### Claude Code plugin marketplace

In **Claude Code** (the CLI, or the VS Code / JetBrains extension). Run these as
**two separate commands, one at a time**:

```
/plugin marketplace add dhk/skill-map
```

```
/plugin install skill-doctor@skill-map
```

Then invoke it with `/skill-doctor`. This does fetch the full skill-map repo
under the hood — prefer the pipx install above if you want to avoid that.

### Shell install

```bash
curl -fsSL https://raw.githubusercontent.com/dhk/skill-map/main/install.sh | bash
```

Clones the whole repo and symlinks the skill into `~/.claude/skills`. Then
invoke with `/skill-doctor`. Prefer the pipx install above unless you
specifically want a live-updating symlink to a full checkout.

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

**pipx install:**
```bash
pipx run dhk-skill-doctor --force   # update
rm -rf ~/.claude/skills/skill-doctor   # remove
```

**Plugin install:**
```
/plugin marketplace update skill-map
/plugin uninstall skill-doctor@skill-map
```

---

## What's inside

```
plugins/skill-doctor/
├── .claude-plugin/plugin.json      # Claude Code plugin manifest
├── pyproject.toml                  # PyPI package (`dhk-skill-doctor`) — installer only
├── src/skill_doctor_installer/     # installer CLI; bundles skills/skill-doctor/ as data
└── skills/skill-doctor/            # the actual skill — single source of truth
    ├── SKILL.md
    ├── WIRING.md
    └── reference/
        ├── rubric.md
        └── interview-bank.md
```

The skill itself is self-contained Markdown — the rubric is carried as prose in
`reference/`, so it runs anywhere with no Python or network access at runtime.
The `pyproject.toml` package exists only to get that Markdown onto your disk
without needing git; it has no runtime dependency on skill-map beyond install
time.

Version: `1.0.1` — pinned explicitly; you only receive updates when that string
bumps (in both `plugin.json` and `pyproject.toml`).

Releases to PyPI are automated: pushing a `skill-doctor-vX.Y.Z` tag runs
[`.github/workflows/publish-skill-doctor.yml`](.github/workflows/publish-skill-doctor.yml),
which builds and publishes via PyPI Trusted Publishing (no stored token). See
[`.github/workflows/README.md`](.github/workflows/README.md) for the one-time
PyPI setup and how to wire up the same flow for future plugins.
