# skill-doctor (plugin)

Interactive best-practice reviewer for a single Claude Agent Skill. It examines a
`SKILL.md`, interviews you about the things the file alone can't reveal —
**allowed-tools scoping, data sensitivity (PHI/PII/HIPAA), high-stakes actions,
triggering, and install scope** — then recommends fixes and applies them on your
confirmation.

Grounded in the [skill-map](https://github.com/dhk/skill-map) study of ~5,000
crawled skills (e.g. >50% of `Bash` grants are unscoped; half of regulated-data
skills ship with no safeguard).

## Install

In **Claude Code** (the CLI or VS Code / JetBrains extension — *not* the Claude
Desktop app or claude.ai, which don't support plugins). Run these as **two
separate commands, one at a time**:

```
/plugin marketplace add dhk/skill-map
```
```
/plugin install skill-doctor@skill-map
```

Then invoke it with `/skill-doctor`, or just ask:
"use skill-doctor on `.claude/skills/foo/SKILL.md`".

Not in Claude Code? See [INSTALL.md](../../INSTALL.md) for the one-line shell
install and troubleshooting.

## Update / remove

```
/plugin marketplace update skill-map
/plugin uninstall skill-doctor@skill-map
```

## What's inside

```
plugins/skill-doctor/
├── .claude-plugin/plugin.json
└── skills/skill-doctor/
    ├── SKILL.md
    └── reference/{rubric,interview-bank}.md
```

The skill is self-contained — the rubric is carried as prose, so it needs no
Python or the skill-map repo at runtime.
