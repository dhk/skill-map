"""
patch_map_badges.py — Refresh the best-practices grade badges embedded in the
live map (index.html GRAPH), joining map skill nodes to the scored corpus by
their source_url. Part of the pipeline so the map stays in sync with scores.

Usage:  python crawlers/patch_map_badges.py
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent.parent
HTML = BASE / 'index.html'
Q = BASE / 'data' / 'skill_quality.json'


def parse(url):
    m = re.match(r'https://github.com/([^/]+/[^/]+)/tree/[^/]+/(.+)', url or '')
    return (m.group(1), m.group(2).rstrip('/') + '/SKILL.md') if m else None


def main():
    html = HTML.read_text()
    m = re.search(r'const GRAPH = (\{.*?\});\n', html, re.S)
    g = json.loads(m.group(1))
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
    html = html[:m.start()] + 'const GRAPH = ' + json.dumps(g, separators=(',', ':')) + ';\n' + html[m.end():]
    HTML.write_text(html)
    print(f'patched {n} map badges')


if __name__ == '__main__':
    main()
