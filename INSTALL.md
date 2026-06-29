# Installing skill-doctor

By **dhk** — <https://github.com/dhk/skill-map>. Pick the path that matches how
much you want to inspect before running.

> **Requires Claude Code** (the CLI, or the VS Code / JetBrains extension).
> Plugins are not available in the **Claude Desktop** app or **claude.ai** — if
> you see `/plugin isn't available in this environment`, you're not in Claude
> Code. On Desktop/web, use the **Shell install** below instead.

---

## One-shot (if you trust the source)

**Plugin (recommended)** — inside Claude Code. Run these as **two separate
commands, one at a time** (don't paste both lines at once):

```
/plugin marketplace add dhk/skill-map
```

```
/plugin install skill-doctor@skill-map
```

**Shell** — works anywhere (incl. Desktop/web users who have the CLI installed).
Clones the repo and symlinks the skill into `~/.claude/skills`:

```bash
curl -fsSL https://raw.githubusercontent.com/dhk/skill-map/main/install.sh | bash
```

Either way, then invoke it with `/skill-doctor`.

---

## claude.ai / the Claude Desktop chat app

The **chat apps** (claude.ai in a browser, and the Claude **Desktop** app) don't
use Claude Code's plugin marketplace. They take custom Skills as a **zip upload**:

1. **Requirements:** a **Pro, Max, Team, or Enterprise** plan with **code
   execution enabled** in settings.
2. **Get the zip:** download [`dist/skill-doctor.zip`](dist/skill-doctor.zip)
   from this repo (or rebuild it with `bash plugins/skill-doctor/build-zip.sh`).
3. **Upload it:** in claude.ai or the Desktop app, go to
   **Settings → Features → Skills** and upload `skill-doctor.zip`.
4. Claude uses it automatically when relevant.

Notes:
- **No auto-update.** Re-upload the zip to get a new version; the chat apps don't
  track this repo or pin a marketplace version.
- **Per-user, per-surface.** A claude.ai upload is separate from Claude Code and
  the API, and each teammate uploads their own copy.
- **No local files.** On claude.ai the skill runs in Claude's VM, so the
  "apply edits in place" step doesn't apply — paste or upload the `SKILL.md` you
  want reviewed, and Claude returns the improved version for you to download.

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

## Troubleshooting

**`/plugin isn't available in this environment.`**
You're in the **Claude Desktop** app or on **claude.ai**, which don't support
plugins. Use Claude Code (the CLI or the VS Code / JetBrains extension), or use
the **Shell install** above — it works anywhere the CLI is installed.

**`fatal: unable to access 'https://github.com/dhk/skill-map /plugin install …'`**
(or any error showing the repo URL with extra text after it). The two commands
got run as **one** — `marketplace add` treated the second line as part of the
repo path. Run them **separately, one at a time**:

```
/plugin marketplace add dhk/skill-map
```

then, after it succeeds:

```
/plugin install skill-doctor@skill-map
```

If you'd rather avoid the two-step flow entirely, use the one-line **Shell
install** above.

---

## Who made this?

skill-doctor is by **dhk** (<https://github.com/dhk>, <dhkonskills@dhk.io>).
Authorship is verifiable in several places:

- The **GitHub repo path** `dhk/skill-map` — only the owner of that account can
  publish under it. The plugin namespace `@skill-map` derives from this repo.
- The **marketplace `owner`** and the plugin **`author`** fields in
  [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) and
  [`plugin.json`](plugins/skill-doctor/.claude-plugin/plugin.json) — Claude Code
  shows these in the `/plugin` UI when you add the marketplace and install.
- Git **commit history** on the repo.

For the strongest guarantee, install from a tagged release commit and verify the
tag, rather than tracking `main`.
