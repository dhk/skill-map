"""
render_copy_network.py — Directed copy network of skill repos.

Replaces the two-column Sankey, which was structurally wrong: both axes were the
same universe (repos), forcing each repo to be either a pure source or a pure
sink. In reality several repos are INTERMEDIARIES — they copy from upstream and
are copied downstream (layered inheritance: authors → aggregators → re-aggregators).

Here each repo is ONE node, sized by skills involved, x-positioned by role
(senders left → receivers right; intermediaries land in the middle). Edges are
copy flows: solid = trustworthy direction (canonical authority or clean dates),
dashed = direction inferred from a bulk-published snapshot (lower confidence).

Usage:  python crawlers/render_copy_network.py [out.png]
"""
import json
import sys
from collections import defaultdict, Counter
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mp

BASE = Path(__file__).parent.parent
LIN = BASE / 'data' / 'lineage.json'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / 'docs' / 'figures' / 'copy-network.png'
CANON = {'anthropics/skills', 'openai/skills'}


def build_edges(d):
    shared = Counter()
    earlier = defaultdict(lambda: [0, 0])
    for c in d['clusters']:
        byrepo = {}
        for m in c['members']:
            if m['first_date'] and (m['repo'] not in byrepo or m['first_date'] < byrepo[m['repo']]):
                byrepo[m['repo']] = m['first_date']
        for a, b in combinations(sorted(byrepo), 2):
            shared[(a, b)] += 1
            if byrepo[a] < byrepo[b]: earlier[(a, b)][0] += 1
            elif byrepo[b] < byrepo[a]: earlier[(a, b)][1] += 1
    bulk = set(d.get('bulk_published_repos', []))
    edges = []
    for (a, b), n in shared.items():
        if n < 2:
            continue
        f, r = earlier[(a, b)]
        src, dst = (a, b) if f >= r else (b, a)
        reliable = (src in CANON) or (src not in bulk)
        edges.append((src, dst, n, reliable))
    return edges


def main():
    d = json.load(open(LIN))
    edges = build_edges(d)
    repos = sorted({r for e in edges for r in e[:2]})
    indeg, outdeg, weight = defaultdict(int), defaultdict(int), defaultdict(int)
    # role is computed from RELIABLE edges only, so bulk-publish date artifacts
    # (e.g. Anthropic's late snapshot looking like an inbound copy) don't shove a
    # known originator into the receiver column. All edges are still drawn.
    rin, rout = defaultdict(int), defaultdict(int)
    for s, t, w, reliable in edges:
        outdeg[s] += 1; indeg[t] += 1; weight[s] += w; weight[t] += w
        if reliable:
            rout[s] += 1; rin[t] += 1

    def role_x(r):
        if r in CANON:
            return 0.0                       # vendors originate, by authority
        o, i = rout[r], rin[r]
        if o + i == 0:
            return 0.5
        return round(0.15 + 0.85 * i / (o + i), 2)
    xs = {r: role_x(r) for r in repos}
    order = sorted(repos, key=lambda r: (xs[r], -weight[r]))
    bands = defaultdict(list)
    for r in order:
        bands[xs[r]].append(r)
    pos = {}
    for band, members in bands.items():
        k = len(members)
        for j, r in enumerate(members):
            y = 0.5 if k == 1 else 0.08 + 0.84 * j / (k - 1)
            pos[r] = (band, y)

    fig, ax = plt.subplots(figsize=(15, 9)); fig.set_facecolor('#f9f8f6'); ax.set_facecolor('#f9f8f6')
    owner = lambda r: r.split('/')[0]

    def nsize(r):
        return 260 + weight[r] * 9

    # edges
    for s, t, w, reliable in edges:
        x0, y0 = pos[s]; x1, y1 = pos[t]
        lw = min(7.0, 0.8 + w * 0.06)        # cap so the 223-skill edge isn't a blob
        ax.annotate('', xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle='-|>', color='#16a34a' if reliable else '#c0594a',
                                    lw=lw, alpha=0.55 if reliable else 0.38,
                                    linestyle='-' if reliable else (0, (5, 3)),
                                    connectionstyle='arc3,rad=0.16',
                                    shrinkA=15, shrinkB=18))
        if w >= 40:                          # label the dominant copy edge
            ax.annotate(f'{w} skills', ((x0 + x1) / 2, (y0 + y1) / 2 + 0.04),
                        fontsize=8, family='monospace', color='#c0594a',
                        ha='center', va='center')
    # nodes
    for r in repos:
        x, y = pos[r]
        canon = r in CANON
        ax.scatter([x], [y], s=nsize(r), c='#2970d6' if canon else '#8a8a8a',
                   edgecolors='white', linewidths=1.2, zorder=3)
        intermediary = indeg[r] > 0 and outdeg[r] > 0 and not canon
        lbl = f'{owner(r)}'
        ax.annotate(lbl, (x, y), fontsize=10.5, family='monospace',
                    weight='bold' if (canon or intermediary) else 'normal',
                    ha='center', va='center',
                    xytext=(0, -15 - (nsize(r)**0.5)/3), textcoords='offset points',
                    color='#111')
        if intermediary:
            ax.annotate(f'↻ in {indeg[r]} / out {outdeg[r]}', (x, y), fontsize=7.5,
                        family='monospace', ha='center', va='center',
                        xytext=(0, 13 + (nsize(r)**0.5)/3), textcoords='offset points', color='#c0594a')

    ax.set_xlim(-0.18, 1.18); ax.set_ylim(-0.35, 1.35); ax.axis('off')
    ax.set_title('Skill Copy Network — who copies whom   '
                 '(node = repo, size = skills involved, arrow = copy direction)',
                 fontsize=13.5, family='monospace', color='#111', pad=14)
    ax.text(-0.18, 1.28, 'Left = mostly originate · Right = mostly receive · Middle = intermediaries (both). '
            'Blue = canonical vendor.', fontsize=9, family='monospace', color='#333')
    ax.text(-0.18, -0.3,
            'Solid green = trustworthy direction (canonical authority or clean commit dates).  '
            'Dashed red = direction inferred from a bulk-published snapshot (lower confidence).\n'
            'The intermediaries (davila7, BbgnsurfTech, QuestForTech) are exactly what the two-column '
            'Sankey hid: repos that both copy and are copied — layered inheritance.',
            fontsize=8.5, family='monospace', color='#5a5850')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(); plt.savefig(OUT, dpi=150, facecolor='#f9f8f6')
    print(f'wrote {OUT}  ({len(repos)} repos, {len(edges)} edges)')


if __name__ == '__main__':
    main()
