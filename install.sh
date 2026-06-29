#!/usr/bin/env bash
#
# skill-doctor installer — https://github.com/dhk/skill-map
# Author: dhk (https://github.com/dhk)
#
# Installs the skill-doctor Agent Skill into ~/.claude/skills by cloning this
# repo and symlinking the skill (so `git pull` updates it). Idempotent.
#
# One-shot:
#   curl -fsSL https://raw.githubusercontent.com/dhk/skill-map/main/install.sh | bash
#
# Override the checkout location with SKILL_MAP_DIR=/path before running.

set -euo pipefail

REPO_URL="https://github.com/dhk/skill-map.git"
SRC_DIR="${SKILL_MAP_DIR:-$HOME/.local/share/skill-map}"
SKILLS_DIR="$HOME/.claude/skills"
SKILL_SRC="$SRC_DIR/plugins/skill-doctor/skills/skill-doctor"
LINK="$SKILLS_DIR/skill-doctor"

say() { printf '\033[1;35m▸\033[0m %s\n' "$1"; }

command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }

if [ -d "$SRC_DIR/.git" ]; then
  say "Updating skill-map in $SRC_DIR"
  git -C "$SRC_DIR" pull --ff-only
else
  say "Cloning skill-map into $SRC_DIR"
  git clone --depth 1 "$REPO_URL" "$SRC_DIR"
fi

mkdir -p "$SKILLS_DIR"

if [ -e "$LINK" ] || [ -L "$LINK" ]; then
  if [ -L "$LINK" ] && [ "$(readlink "$LINK")" = "$SKILL_SRC" ]; then
    say "Symlink already in place"
  else
    echo "Refusing to overwrite existing $LINK (not our symlink)." >&2
    echo "Remove it yourself and re-run if you want to replace it." >&2
    exit 1
  fi
else
  ln -s "$SKILL_SRC" "$LINK"
  say "Linked $LINK -> $SKILL_SRC"
fi

cat <<EOF

✅ skill-doctor installed.

   Invoke it in Claude Code:  /skill-doctor
   or ask: "use skill-doctor on path/to/SKILL.md"

   Update later:   git -C "$SRC_DIR" pull
   Uninstall:      rm "$LINK"

   By dhk · https://github.com/dhk/skill-map
EOF
