"""
tag_skills.py — Classify skill nodes along 4 ontology dimensions using Claude CLI.

Dimensions:
  action        : what the skill does (generate|extract|transform|automate|analyze|configure|integrate)
  complexity    : barrier to entry (foundational|intermediate|advanced)
  output_type   : what it produces (text|code|structured-data|media|action|report)
  integration   : how it connects (standalone|connector|orchestrator|modifier)

Uses `claude -p` (no API key needed — uses existing Claude Code OAuth session).
Results cached in data/skill_tags.json so re-runs are incremental.

Usage:
    python crawlers/tag_skills.py              # tag all untagged skills
    python crawlers/tag_skills.py --force      # re-tag everything
    python crawlers/tag_skills.py --dry-run    # print prompts, don't call claude
    python crawlers/tag_skills.py --patch      # patch tags into index.html GRAPH JSON
"""
import json, re, os, subprocess, argparse, sys, time
from pathlib import Path

BASE = Path(__file__).parent.parent
HTML_PATH  = BASE / 'index.html'
CACHE_PATH = BASE / 'data' / 'skill_tags.json'

DIMENSIONS = {
    "action":       ["generate", "extract", "transform", "automate", "analyze", "configure", "integrate"],
    "complexity":   ["foundational", "intermediate", "advanced"],
    "output_type":  ["text", "code", "structured-data", "media", "action", "report"],
    "integration":  ["standalone", "connector", "orchestrator", "modifier"],
}

PROMPT_TEMPLATE = """Classify this Claude AI skill along exactly 4 dimensions.
Reply with ONLY a JSON object — no explanation, no markdown, no prose.

Skill name: {label}
Domain: {domain}
Description: {description}

Dimensions and allowed values:
  action      : {action}
  complexity  : {complexity}
  output_type : {output_type}
  integration : {integration}

Reply format: {{"action":"...","complexity":"...","output_type":"...","integration":"..."}}"""


def load_graph():
    content = HTML_PATH.read_text()
    m = re.search(r'const GRAPH = (\{.*?\});\n', content)
    if not m:
        sys.exit("Could not find GRAPH in index.html")
    return json.loads(m.group(1)), content, m


def load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def build_prompt(skill):
    return PROMPT_TEMPLATE.format(
        label=skill.get('label', skill['id']),
        domain=skill.get('domain', ''),
        description=(skill.get('description', '') or '')[:300],
        **{k: '|'.join(v) for k, v in DIMENSIONS.items()},
    )


def call_claude(prompt, dry_run=False):
    if dry_run:
        print(f"  [dry-run] would call: claude -p '{prompt[:80]}...'")
        return {"action": "generate", "complexity": "foundational",
                "output_type": "text", "integration": "standalone"}
    result = subprocess.run(
        ['claude', '-p', prompt],
        capture_output=True, text=True, timeout=30,
    )
    raw = result.stdout.strip()
    # Extract JSON from response (claude might add surrounding text)
    m = re.search(r'\{[^{}]+\}', raw)
    if not m:
        raise ValueError(f"No JSON in response: {raw!r}")
    tags = json.loads(m.group(0))
    # Validate values
    for dim, allowed in DIMENSIONS.items():
        if tags.get(dim) not in allowed:
            tags[dim] = allowed[0]  # fallback to first allowed value
    return tags


def patch_html(graph, content, match, cache):
    for node in graph['nodes']:
        if node['type'] not in ('skill', 'dhk'):
            continue
        if node['id'] in cache:
            node.update(cache[node['id']])
    out = json.dumps(graph, separators=(',', ':'))
    new_content = content[:match.start(1)] + out + content[match.end(1):]
    HTML_PATH.write_text(new_content)
    print(f"Patched index.html with tags from {len(cache)} cached skills.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force',   action='store_true', help='Re-tag already-cached skills')
    parser.add_argument('--dry-run', action='store_true', help='Print prompts without calling claude')
    parser.add_argument('--patch',   action='store_true', help='Only patch index.html from cache, no new tagging')
    args = parser.parse_args()

    graph, content, match = load_graph()
    cache = load_cache()

    skills = [n for n in graph['nodes'] if n['type'] in ('skill', 'dhk')]
    print(f"Skills: {len(skills)} total, {len(cache)} cached")

    if args.patch:
        patch_html(graph, content, match, cache)
        return

    to_tag = [s for s in skills if args.force or s['id'] not in cache]
    print(f"Tagging {len(to_tag)} skills...")

    errors = 0
    for i, skill in enumerate(to_tag, 1):
        prompt = build_prompt(skill)
        print(f"  [{i}/{len(to_tag)}] {skill['id']}", end=' ', flush=True)
        try:
            tags = call_claude(prompt, dry_run=args.dry_run)
            cache[skill['id']] = tags
            print(f"→ {tags}")
            if not args.dry_run and i % 10 == 0:
                save_cache(cache)
            time.sleep(0.3)  # be gentle
        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1

    save_cache(cache)
    print(f"\nDone. {len(to_tag) - errors} tagged, {errors} errors.")
    print(f"Cache saved to {CACHE_PATH}")
    print(f"\nNow run:  python crawlers/tag_skills.py --patch")
    print(f"to write tags into index.html.")


if __name__ == '__main__':
    main()
