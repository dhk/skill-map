# Installing skill-doctor

By **dhk** — <https://github.com/dhk/skill-map>. Pick the path that matches how
much you want to inspect before running.

---

## One-shot (if you trust the source)

**Plugin (recommended)** — inside Claude Code:

```
/plugin marketplace add dhk/skill-map
/plugin install skill-doctor@skill-map
```

**Shell** — clones the repo and symlinks the skill into `~/.claude/skills`:

```bash
curl -fsSL https://raw.githubusercontent.com/dhk/skill-map/main/install.sh | bash
```

Either way, then invoke it with `/skill-doctor`.

---

## Step by step (for the conservative)

Verify before you run anything.

1. **Look at the source.** The repo is <https://github.com/dhk/skill-map>. Read
   the skill itself — it's plain Markdown, no code that executes on install:
   - [`SKILL.md`](plugins/skill-doctor/skills/skill-doctor/SKILL.md)
   - [`reference/rubric.md`](plugins/skill-doctor/skills/skill-doctor/reference/rubric.md)
   - [`reference/interview-bank.md`](plugins/skill-doctor/skills/skill-doctor/reference/interview-bank.md)

2. **Read the installer** before piping it to a shell:
   <https://github.com/dhk/skill-map/blob/main/install.sh>

3. **Add the marketplace and review it** — adding a marketplace does *not*
   install anything; it just registers the catalog so you can inspect it:
   ```
   /plugin marketplace add dhk/skill-map
   ```
   Then open the `/plugin` menu, find `skill-doctor@skill-map`, and check the
   author and contents.

4. **Install when satisfied:**
   ```
   /plugin install skill-doctor@skill-map
   ```

5. **Or install fully by hand** (no marketplace, no script):
   ```bash
   git clone https://github.com/dhk/skill-map ~/.local/share/skill-map
   ln -s ~/.local/share/skill-map/plugins/skill-doctor/skills/skill-doctor \
         ~/.claude/skills/skill-doctor
   ```

### Pin a version

The plugin is published with an explicit `version` (currently `1.0.0`), so you
only receive updates when that string is bumped — nothing changes under you. To
pin to an exact commit instead, add the marketplace from a specific `ref`/`sha`
(see the [marketplace docs](https://code.claude.com/docs/en/plugin-marketplaces)).

---

## Who made this?

skill-doctor is by **dhk** (<https://github.com/dhk>). Authorship is verifiable
in several places:

- The **GitHub repo path** `dhk/skill-map` — only the owner of that account can
  publish under it. The plugin namespace `@skill-map` derives from this repo.
- The **marketplace `owner`** and the plugin **`author`** fields in
  [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) and
  [`plugin.json`](plugins/skill-doctor/.claude-plugin/plugin.json) — Claude Code
  shows these in the `/plugin` UI when you add the marketplace and install.
- Git **commit history** on the repo.

For the strongest guarantee, install from a tagged release commit and verify the
tag, rather than tracking `main`.
