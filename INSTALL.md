# Installing skill-doctor

By **dhk** — <https://github.com/dhk/skill-map>.

---

## 1. One-shot install (recommended)

```bash
pipx run dhk-skill-doctor
```

Repo-free: the skill content ships as data inside the `dhk-skill-doctor` PyPI
wheel, so this fetches it, runs the installer once in a throwaway venv, and
leaves nothing behind but `~/.claude/skills/skill-doctor`. No git required.
Then invoke it with `/skill-doctor` in Claude Code.

Re-run the same command to update. Add `--force` if you've hand-edited the
installed copy and want to reset it; `--target <dir>` to install somewhere
other than the default.

## 2. Fallback: curl one-liner (if you don't have `pipx`)

```bash
curl -fsSL https://raw.githubusercontent.com/dhk/skill-map/main/install.sh | bash
```

Clones this repo with git and symlinks the skill into `~/.claude/skills`
(so `git pull` in the checkout updates it). Use this when `pipx`/Python isn't
available but git is. Get `pipx` instead with `pip install pipx && pipx
ensurepath` — see the [pipx docs](https://pipx.pypa.io/stable/installation/).

## 3. Detailed guide

Everything below — the Claude Code plugin marketplace path, the claude.ai/
Desktop zip upload, a verify-before-you-run walkthrough, version pinning, and
troubleshooting — for when you want more control than the one-liners above.

> **Plugin marketplace requires Claude Code** (the CLI, or the VS Code /
> JetBrains extension). Plugins aren't available in the Claude Desktop app or
> claude.ai — use the zip upload section below on those surfaces.

### Claude Code plugin marketplace

Inside Claude Code. Run these as **two separate commands, one at a time**
(don't paste both lines at once):

```
/plugin marketplace add dhk/skill-map
```

```
/plugin install skill-doctor@skill-map
```

Then invoke it with `/skill-doctor`. Note this fetches the *full* skill-map
repo under the hood (crawler, data, docs — everything) — prefer options 1 or 2
above if you want to avoid that.

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

2. **For the `pipx` path**, read the installer it runs — it's ~50 lines, no
   third-party dependencies, and only ever writes under `~/.claude/skills/`:
   [`src/skill_doctor_installer/cli.py`](plugins/skill-doctor/src/skill_doctor_installer/cli.py).
   The PyPI package (`dhk-skill-doctor`) is built straight from this repo via CI —
   [`pyproject.toml`](plugins/skill-doctor/pyproject.toml) bundles the same
   `skills/skill-doctor/` tree linked above as package data, nothing more.

3. **For the shell-install path**, read the installer before piping it to a
   shell: <https://github.com/dhk/skill-map/blob/main/install.sh>

4. **Add the marketplace and review it** — adding a marketplace does *not*
   install anything; it just registers the catalog so you can inspect it:
   ```
   /plugin marketplace add dhk/skill-map
   ```
   Then open the `/plugin` menu, find `skill-doctor@skill-map`, and check the
   author and contents.

5. **Install when satisfied**, via whichever path you verified:
   ```bash
   pipx run dhk-skill-doctor
   ```
   ```
   /plugin install skill-doctor@skill-map
   ```

6. **Or install fully by hand** (no marketplace, no installer script):
   ```bash
   git clone https://github.com/dhk/skill-map ~/.local/share/skill-map
   ln -s ~/.local/share/skill-map/plugins/skill-doctor/skills/skill-doctor \
         ~/.claude/skills/skill-doctor
   ```

### Pin a version

Every distribution channel carries the same explicit `version` string
(currently `1.0.0`) in lockstep — `plugin.json`, `pyproject.toml`, and
`SKILL.md` — so you only receive updates when that string bumps; nothing
changes under you between runs.

- **pipx:** `pipx run "dhk-skill-doctor==1.0.0"` pins to an exact release.
- **Plugin:** add the marketplace from a specific `ref`/`sha` instead of
  `main` (see the [marketplace docs](https://code.claude.com/docs/en/plugin-marketplaces)).

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
