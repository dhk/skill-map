"""
gen_types.py — Quality sliced by skill type (heuristic, from the skill name).
Writes data/skill_types.json. Part of the pipeline.

Usage:  python crawlers/gen_types.py
"""
import json
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent.parent
Q = BASE / 'data' / 'skill_quality.json'
OUT = BASE / 'data' / 'skill_types.json'

TYPES = [
    ('reviewer/auditor', r'review|audit|lint|critique|inspect|analy'),
    ('generator/creator', r'generat|creat|build|scaffold|draft|writ|design|render'),
    ('transformer/converter', r'convert|transform|format|migrat|refactor|translat|parse'),
    ('integration/connector', r'api|connect|integrat|webhook|client|sdk|mcp|oauth'),
    ('workflow/orchestrator', r'workflow|orchestrat|pipeline|automat|deploy|ci|release|agent'),
    ('reference/guide', r'guide|reference|cheat|doc|tip|best.?practice|standard|convention'),
    ('test/quality', r'test|qa|coverage|e2e|playwright|cypress|spec'),
    ('data/analytics', r'data|sql|analy|report|metric|dashboard|query|etl'),
]


def stype(name):
    n = (name or '').lower()
    for t, pat in TYPES:
        if re.search(pat, n):
            return t
    return 'other/domain'


def main():
    skills = json.load(open(Q))['skills']
    by = defaultdict(list)
    for s in skills:
        by[stype(s['name'])].append(s)
    out = {}
    for t, items in by.items():
        ov = [x['overall'] for x in items]
        when = 100 * sum(x['desc_has_when'] for x in items) / len(items)
        out[t] = {'n': len(items), 'median': round(st.median(ov), 1),
                  'pct_when': round(when, 1)}
    OUT.write_text(json.dumps(out, indent=1))
    print(f'wrote {OUT} ({len(out)} types)')


if __name__ == '__main__':
    main()
