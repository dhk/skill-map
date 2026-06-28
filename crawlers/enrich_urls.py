"""
enrich_urls.py — Add source_url to skill nodes in index.html using crawl data.

For each skill, finds the best matching crawl result and sets source_url to the
actual GitHub URL (repo_url + file directory path). Falls back to linking to the
credited org page when no crawl match exists.

Usage:
    python crawlers/enrich_urls.py [--crawl crawls/crawl-1-2026-06-24/data.json]
"""
import json, re, os, argparse
from collections import defaultdict

REPO_ROOT = os.path.join(os.path.dirname(__file__), '..')
HTML_PATH  = os.path.join(REPO_ROOT, 'index.html')
DEFAULT_CRAWL = os.path.join(REPO_ROOT, 'crawls/crawl-1-2026-06-24/data.json')

parser = argparse.ArgumentParser()
parser.add_argument('--crawl', default=DEFAULT_CRAWL)
args = parser.parse_args()

# ── Load crawl data ──────────────────────────────────────────────
with open(args.crawl) as f:
    crawl_data = json.load(f)
results = crawl_data['results']

# REVIEW(fragile): nodes are matched to crawl results by the skill's DIRECTORY
# NAME alone (last path segment). Many repos name skills identically (dozens of
# "pdf", "review", "test" dirs), so pick_best falls back to org-name heuristics
# and can attach the wrong repo's URL to a node. The graph node ids include the
# org (org/skill) — match on (org, dir) at minimum, or carry the real (repo,
# file_path) key from the crawl rather than re-keying on a non-unique basename.
# Build index: skill_dir_name -> list of crawl results (exclude hidden dirs)
by_dir = defaultdict(list)
for r in results:
    parts = r['file_path'].split('/')
    if len(parts) < 2:
        continue
    skill_dir = parts[-2]
    if skill_dir.startswith('.'):
        continue
    by_dir[skill_dir].append(r)

def pick_best(skill_id, candidates):
    """Prefer: exact org match > canonical source > first result."""
    org = skill_id.split('/')[0].lower()
    for r in candidates:
        if r['repo_full_name'].split('/')[0].lower() == org and r['repo_source'] == 'canonical':
            return r
    for r in candidates:
        if r['repo_full_name'].split('/')[0].lower() == org:
            return r
    for r in candidates:
        if r['repo_source'] == 'canonical':
            return r
    return candidates[0] if candidates else None

def make_source_url(skill_id, result):
    """Build a clickable GitHub tree URL from repo_url + file directory."""
    repo_url = result['repo_url'].rstrip('/')
    # file_path like "skills/docx/SKILL.md" -> directory "skills/docx"
    parts = result['file_path'].split('/')
    skill_dir_path = '/'.join(parts[:-1])  # strip SKILL.md
    # REVIEW(fragile): hard-codes "/tree/main/". Any repo whose default branch is
    # master/develop/etc. gets a 404 source link. The crawl uses /HEAD/ for raw
    # URLs (which would work here too), and get_repo_meta could capture
    # default_branch outright (see crawl.py note). patch_map_badges.py then parses
    # these URLs with /tree/[^/]+/ — i.e. it already tolerates any branch on READ
    # but enrich only ever WRITES "main", so the two disagree by construction.
    return f"{repo_url}/tree/main/{skill_dir_path}"

def fallback_url(skill_id):
    """Link to the credited org when we have no crawl match."""
    org = skill_id.split('/')[0]
    return f"https://github.com/{org}"

# ── Load and patch index.html ────────────────────────────────────
with open(HTML_PATH) as f:
    content = f.read()

match = re.search(r'const GRAPH = ({.*?});\n', content)
graph = json.loads(match.group(1))

matched = 0
fallback = 0
for node in graph['nodes']:
    if node['type'] not in ('skill', 'dhk'):
        continue
    skill_dir = node['id'].split('/')[-1]
    candidates = by_dir.get(skill_dir, [])
    best = pick_best(node['id'], candidates)
    if best:
        node['source_url'] = make_source_url(node['id'], best)
        matched += 1
    else:
        node['source_url'] = fallback_url(node['id'])
        fallback += 1

print(f"Matched from crawl: {matched}, Fallback to org page: {fallback}")

out = json.dumps(graph, separators=(',', ':'))
new_content = content[:match.start(1)] + out + content[match.end(1):]
with open(HTML_PATH, 'w') as f:
    f.write(new_content)
print("Done — index.html updated with source_url on all skill nodes.")
