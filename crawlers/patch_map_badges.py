"""
patch_map_badges.py — Refresh the best-practices grade badges embedded in the
live map (index.html GRAPH), joining map skill nodes to the scored corpus by
their source_url. Part of the pipeline so the map stays in sync with scores.

Usage:  python crawlers/patch_map_badges.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from graphio import load_graph, save_graph

BASE = Path(__file__).parent.parent
Q = BASE / 'data' / 'skill_quality.json'


def parse(url):
    m = re.match(r'https://github.com/([^/]+/[^/]+)/tree/[^/]+/(.+)', url or '')
    return (m.group(1), m.group(2).rstrip('/') + '/SKILL.md') if m else None


def main():
    g, content, match = load_graph()
    qmap = {(s['repo'], s['file_path']): s for s in json.load(open(Q))['skills']}
    n = 0
    for node in g['nodes']:
        if node.get('type') != 'skill':
            continue
        s = qmap.get(parse(node.get('source_url')) or ('', ''))
        if s:
            node['bp_grade'] = s['grade']
            node['bp_score'] = s['overall']
            n += 1
    # RECOMMEND(review2, P1): this matched 26/39 graded nodes after the
    # merged-corpus + graphio changes (was 39/39 on main). The other 13 keep
    # STALE grades from a prior run instead of being refreshed. Likely the
    # source_url → (repo, file_path) join drops rows now (branch/path mismatch
    # vs the merged corpus keys). Investigate the parse() join; report matched
    # vs total (e.g. f'patched {n}/{graded} map badges') so a drop is visible.
    save_graph(g, content, match)
    print(f'patched {n} map badges')


if __name__ == '__main__':
    main()
