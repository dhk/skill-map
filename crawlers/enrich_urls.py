"""
enrich_urls.py — Add source_url to skill nodes in index.html using crawl data.

For each skill node, find the best matching crawl result and set source_url to the
real GitHub tree URL (repo_url + skill directory). Falls back to the credited org
page when no crawl match exists.

Matching is keyed on (org, skill-dir) — the node id is `org/skill`, so this avoids
the cross-repo basename collisions a dir-name-only match caused. Branch comes from
the crawl-captured default_branch (HEAD fallback) instead of a hard-coded "main".

Usage:
    python crawlers/enrich_urls.py            # merged corpus
    python crawlers/enrich_urls.py --crawl crawls/crawl-1-2026-06-24/data.json
"""
import json
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from graphio import load_graph, save_graph, skill_nodes
from score_corpus import load_all_crawls


def build_index(results):
    """(org_lower, skill_dir) -> [crawl results]. Skips hidden dirs."""
    idx = defaultdict(list)
    for r in results:
        parts = r['file_path'].split('/')
        if len(parts) < 2:
            continue
        skill_dir = parts[-2]
        if skill_dir.startswith('.'):
            continue
        org = r['repo_full_name'].split('/')[0].lower()
        idx[(org, skill_dir)].append(r)
    return idx


def pick_best(candidates):
    """Prefer a canonical source; else the first match."""
    for r in candidates:
        if r.get('repo_source') == 'canonical':
            return r
    return candidates[0] if candidates else None


def make_source_url(result):
    repo_url = result['repo_url'].rstrip('/')
    skill_dir_path = '/'.join(result['file_path'].split('/')[:-1])  # strip SKILL.md
    branch = result.get('repo_default_branch') or 'HEAD'
    return f"{repo_url}/tree/{branch}/{skill_dir_path}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--crawl', help='single crawl data.json (default: merged corpus)')
    args = ap.parse_args()

    if args.crawl:
        results = json.load(open(args.crawl))['results']
    else:
        results = load_all_crawls()
    index = build_index(results)

    graph, content, match = load_graph()
    matched = fallback = 0
    for node in skill_nodes(graph):
        org = node['id'].split('/')[0].lower()
        skill_dir = node['id'].split('/')[-1]
        best = pick_best(index.get((org, skill_dir), []))
        if best:
            node['source_url'] = make_source_url(best)
            matched += 1
        else:
            node['source_url'] = f"https://github.com/{node['id'].split('/')[0]}"
            fallback += 1

    save_graph(graph, content, match)
    print(f"source_url set — matched from crawl: {matched}, org-page fallback: {fallback}")


if __name__ == '__main__':
    main()
