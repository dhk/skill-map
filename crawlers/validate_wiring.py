#!/usr/bin/env python3
"""
validate_wiring.py — validate a WIRING.md file against the schema.

Usage:
  python crawlers/validate_wiring.py path/to/WIRING.md [path/to/WIRING.md ...]
  python crawlers/validate_wiring.py --all          # find and validate all WIRING.md in repo

Exit codes:
  0  all valid
  1  schema validation error
  2  broken skill reference (warning, not error)
"""

import sys
import re
import json
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pip install pyyaml")

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    print("Warning: jsonschema not installed — structural validation skipped. pip install jsonschema")


REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "wiring.schema.json"

FRONTMATTER_RE = re.compile(r'^---\s*\n(.*?)\n---', re.DOTALL)


def load_schema():
    if not SCHEMA_PATH.exists():
        return None
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def parse_wiring(path: Path) -> dict | None:
    """Extract and parse the YAML front-matter from a WIRING.md file."""
    text = path.read_text(encoding='utf-8')
    m = FRONTMATTER_RE.match(text)
    if not m:
        print(f"  ERROR: no YAML front-matter found (expected --- block at top)")
        return None
    try:
        return yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        print(f"  ERROR: YAML parse error: {e}")
        return None


def validate_schema(data: dict, schema: dict) -> list[str]:
    errors = []
    if not HAS_JSONSCHEMA:
        # Manual minimal check
        for field in ("spec", "type", "name", "description"):
            if field not in data:
                errors.append(f"Missing required field: {field}")
        if data.get("spec") != "0.1":
            errors.append(f"spec must be '0.1', got {data.get('spec')!r}")
        if data.get("type") not in ("router", "workflow", "ensemble"):
            errors.append(f"type must be router|workflow|ensemble, got {data.get('type')!r}")
        t = data.get("type")
        if t == "router" and "routes" not in data:
            errors.append("router requires 'routes'")
        if t == "router" and "entry" not in data:
            errors.append("router requires 'entry'")
        if t == "workflow" and "steps" not in data:
            errors.append("workflow requires 'steps'")
        if t == "ensemble" and "members" not in data:
            errors.append("ensemble requires 'members'")
        return errors

    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        errors.append(e.message)
    return errors


def check_references(data: dict, wiring_path: Path) -> list[str]:
    """Warn about skill references that can't be resolved locally."""
    warnings = []
    skills_dir = REPO_ROOT / ".claude" / "skills"

    def check_skill(skill: str, repo: str | None):
        if repo:
            return  # external — can't resolve locally
        if '/' in skill:
            return  # inline owner/repo/skill shorthand
        local = REPO_ROOT / "plugins" / skill / "skills" / skill / "SKILL.md"
        symlink = skills_dir / skill / "SKILL.md"
        if not local.exists() and not symlink.exists():
            warnings.append(f"  WARN: skill '{skill}' not found locally (may be installed elsewhere)")

    wtype = data.get("type")
    if wtype == "router":
        for route in data.get("routes", []):
            if "skill" in route:
                check_skill(route["skill"], route.get("repo"))
            for s in route.get("skills", []):
                check_skill(s, route.get("repo"))
    elif wtype == "workflow":
        for step in data.get("steps", []):
            check_skill(step["skill"], step.get("repo"))
    elif wtype == "ensemble":
        for member in data.get("members", []):
            check_skill(member["skill"], member.get("repo"))

    return warnings


def validate_file(path: Path, schema: dict | None) -> bool:
    print(f"\n{path}")
    data = parse_wiring(path)
    if data is None:
        return False

    errors = validate_schema(data, schema) if schema else []
    warnings = check_references(data, path)

    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        return False

    for w in warnings:
        print(w)

    wtype = data.get("type", "?")
    name = data.get("name", "?")
    count = (
        len(data.get("routes", [])) if wtype == "router" else
        len(data.get("steps", [])) if wtype == "workflow" else
        len(data.get("members", [])) if wtype == "ensemble" else 0
    )
    label = "routes" if wtype == "router" else "steps" if wtype == "workflow" else "members"
    print(f"  OK  [{wtype}] {name} — {count} {label}")
    return True


def find_all_wirings() -> list[Path]:
    return list(REPO_ROOT.rglob("WIRING.md"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="WIRING.md file(s) to validate")
    parser.add_argument("--all", action="store_true", help="Find and validate all WIRING.md in repo")
    args = parser.parse_args()

    schema = load_schema()
    if schema is None:
        print(f"Warning: schema not found at {SCHEMA_PATH} — structural validation skipped")

    paths: list[Path] = []
    if args.all:
        paths = find_all_wirings()
        if not paths:
            print("No WIRING.md files found in repo.")
            sys.exit(0)
    elif args.files:
        paths = [Path(f) for f in args.files]
    else:
        parser.print_help()
        sys.exit(0)

    results = [validate_file(p, schema) for p in paths]
    failed = sum(1 for r in results if not r)

    print(f"\n{'─' * 40}")
    print(f"Validated {len(paths)} file(s). {len(paths) - failed} passed, {failed} failed.")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
