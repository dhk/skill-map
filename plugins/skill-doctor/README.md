# skill-doctor (plugin + pip package)

See **[SKILL-DOCTOR.md](../../SKILL-DOCTOR.md)** for the full description, install
guide, and what it checks. Shortest path: `pipx run dhk-skill-doctor`.

## What's inside

```
plugins/skill-doctor/
├── .claude-plugin/plugin.json      # Claude Code plugin manifest
├── pyproject.toml                  # PyPI package `dhk-skill-doctor` — installer only
├── src/skill_doctor_installer/     # installer CLI (entry point: `dhk-skill-doctor`)
└── skills/skill-doctor/            # the actual skill — single source of truth
    ├── SKILL.md
    ├── WIRING.md
    └── reference/
        ├── rubric.md
        └── interview-bank.md
```

The skill itself is self-contained — the rubric is carried as prose in
`reference/`, so it needs no Python or network access at runtime. The pip
package under `src/` exists purely to get `skills/skill-doctor/` onto disk
without cloning this repo: it bundles that same directory as wheel data (see
the `force-include` mapping in `pyproject.toml`) and copies it to
`~/.claude/skills/skill-doctor` when run.

## Update / remove

**pipx:**
```bash
pipx run dhk-skill-doctor --force   # update
rm -rf ~/.claude/skills/skill-doctor   # remove
```

**Plugin:**
```
/plugin marketplace update skill-map
/plugin uninstall skill-doctor@skill-map
```
