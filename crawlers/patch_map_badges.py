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
    matched = cleared = 0
    for node in g['nodes']:
        if node.get('type') != 'skill':
            continue
        s = qmap.get(parse(node.get('source_url')) or ('', ''))
        if s:
            node['bp_grade'] = s['grade']
            node['bp_score'] = s['overall']
            matched += 1
        elif node.pop('bp_grade', None) is not None:
            # Clear a stale/wrong badge rather than leave it from a prior run.
            node.pop('bp_score', None)
            cleared += 1
    # RECOMMEND(review2, P1): symptom fixed here — unmatched nodes no longer keep
    # STALE grades, and we log matched/cleared so a drop is visible. ROOT CAUSE is
    # upstream in enrich_urls: the (org,dir) rewrite drops the deep-link for ~16
    # nodes whose crawled SKILL.md lives in a mega-collection *copy* (attributed to
    # org X but fetched from davila7/affaan-m/...), so they fall back to a bare org
    # URL and no longer join the corpus. Real COVERAGE fix: link to the skill's
    # ACTUAL crawled repo+path, keep the attributed org as a label only. See
    # docs/CODE-REVIEW-RESPONSE.md (P1 #2).
    save_graph(g, content, match)
    print(f'patched {matched} map badges; cleared {cleared} stale')


if __name__ == '__main__':
    main()
