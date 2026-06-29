#!/usr/bin/env bash
#
# Build skill-doctor.zip for upload to claude.ai / the Claude Desktop chat app
# (Settings > Features > Skills). The zip contains the skill folder with SKILL.md
# and its reference/ files at the top level.
#
# Reproducible: run from anywhere, writes dist/skill-doctor.zip at the repo root.
# Keep the skill's version in plugin.json / SKILL.md as the source of truth.

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$here/../.." && pwd)"
src="$here/skills/skill-doctor"
out_dir="$repo_root/dist"
out="$out_dir/skill-doctor.zip"

mkdir -p "$out_dir"
rm -f "$out"

# Zip the folder itself (so the archive expands to skill-doctor/SKILL.md ...).
# -X strips extra file attributes for a stable, reproducible archive.
( cd "$here/skills" && zip -r -X "$out" skill-doctor \
    -x '*.DS_Store' >/dev/null )

echo "Wrote $out"
unzip -l "$out"
