# skill-doctor (plugin)

See **[SKILL-DOCTOR.md](../../SKILL-DOCTOR.md)** for the full description, install
guide, and what it checks.

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
it needs no Python or the skill-map repo at runtime.

## Update / remove

```
/plugin marketplace update skill-map
/plugin uninstall skill-doctor@skill-map
```
