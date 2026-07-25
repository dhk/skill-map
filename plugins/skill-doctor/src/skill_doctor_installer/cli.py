from __future__ import annotations

import argparse
import shutil
import sys
from importlib.resources import as_file, files
from pathlib import Path

MARKER = ".installed-by-skill-doctor-pip"


def _default_target() -> Path:
    return Path.home() / ".claude" / "skills" / "skill-doctor"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dhk-skill-doctor",
        description="Install the skill-doctor Claude Agent Skill into ~/.claude/skills.",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=_default_target(),
        help="destination directory (default: ~/.claude/skills/skill-doctor)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing directory even if it wasn't placed by this tool",
    )
    args = parser.parse_args(argv)

    bundled = files("skill_doctor_installer") / "_bundled"
    if not bundled.is_dir():
        print("error: bundled skill files missing from this package", file=sys.stderr)
        return 1

    dest: Path = args.target
    if dest.exists():
        owned = (dest / MARKER).exists()
        if not owned and not args.force:
            print(f"refusing to overwrite {dest} (not installed by skill-doctor).", file=sys.stderr)
            print("remove it yourself first, or re-run with --force.", file=sys.stderr)
            return 1
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    with as_file(bundled) as bundled_path:
        shutil.copytree(bundled_path, dest)
    (dest / MARKER).write_text(
        "placed by `pipx run dhk-skill-doctor` — safe to overwrite on update or --force\n"
    )

    print(f"skill-doctor installed -> {dest}")
    print()
    print("Invoke it in Claude Code:  /skill-doctor")
    print('or ask: "use skill-doctor on path/to/SKILL.md"')
    print()
    print("Update:      pipx run dhk-skill-doctor --force")
    print(f"Uninstall:   rm -rf {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
