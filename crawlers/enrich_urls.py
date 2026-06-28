"""
enrich_urls.py — Add source_url to skill nodes in index.html using crawl data.

For each skill node, find the best matching crawl result and set source_url to the
real GitHub tree URL (repo_url + skill directory). Falls back to the credited org
page when no crawl match exists.

Matching, in order of preference:
  1. (org, skill-dir) — the node id is `org/skill`; exact attribution match.
  2. skill-dir in ANY repo — the skill's ACTUAL crawled location. Many map nodes
     attribute a skill to org X, but the only crawled copy lives in a
     mega-collection (davila7, affaan-m, …). Linking there is a REAL deep-link to
     where the content exists (org stays the node's label); this restores the ~16
     deep-links/badges the strict (org,dir)-only match dropped — WITHOUT the old
     wrong-repo guessing, because we rank by canonical > stars.
  3. org page — only when the skill isn't in the corpus at all.

Branch comes from the crawl-captured default_branch (HEAD fallback), not a
hard-coded "main".

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
    """Two indexes: by (org_lower, skill_dir) and by skill_dir. Skips hidden dirs."""
    by_org_dir = defaultdict(list)
    by_dir = defaultdict(list)
    for r in results:
        parts = r['file_path'].split('/')
        if len(parts) < 2:
            continue
        skill_dir = parts[-2]
        if skill_dir.startswith('.'):
            continue
        org = r['repo_full_name'].split('/')[0].lower()
        by_org_dir[(org, skill_dir)].append(r)
        by_dir[skill_dir].append(r)
    return by_org_dir, by_dir


def pick_best(candidates):
    """Rank: canonical source > most-starred repo > first. Picks the most
    authoritative ACTUAL location of the skill, not a random cross-repo guess."""
    if not candidates:
        return None
    for r in candidates:
        if r.get('repo_source') == 'canonical':
            return r
    return max(candidates, key=lambda r: r.get('repo_stars') or 0)


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
    by_org_dir, by_dir = build_index(results)

    graph, content, match = load_graph()
    exact = located = fallback = 0
    for node in skill_nodes(graph):
        org = node['id'].split('/')[0].lower()
        skill_dir = node['id'].split('/')[-1]
        best = pick_best(by_org_dir.get((org, skill_dir), []))
        if best:
            exact += 1
        else:
            best = pick_best(by_dir.get(skill_dir, []))   # actual crawled location
            if best:
                located += 1
        if best:
            node['source_url'] = make_source_url(best)
        else:
            node['source_url'] = f"https://github.com/{node['id'].split('/')[0]}"
            fallback += 1

    save_graph(graph, content, match)
    print(f"source_url set — exact (org,dir): {exact}, "
          f"located in corpus: {located}, org-page fallback: {fallback}")


if __name__ == '__main__':
    main()
