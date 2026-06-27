"""
render_sankey.py — Static Sankey of the direction-reliable skill copy flows.

Renders data/lineage.json's `flows` (canonical-authority + clean-date edges only)
as a PNG hero figure for the lineage study. Pure matplotlib — no browser needed
(the env has no Chrome, so D3/kaleido/playwright export is unavailable).

Sources (left) = where skills were first authored; sinks (right) = repos that
copied them; band width = number of skills. The big bulk-published
BbgnsurfTech↔davila7 batch is intentionally excluded — its direction is unprovable.

Usage:  python crawlers/render_sankey.py [out.png]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
import matplotlib.patches as mp

BASE = Path(__file__).parent.parent
LIN = BASE / 'data' / 'lineage.json'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / 'docs' / 'figures' / 'sankey-lineage.png'
GAP = 0.55
PAL = ['#4e79a7', '#59a14f', '#e15759', '#76b7b2', '#edc948',
       '#b07aa1', '#ff9da7', '#9c755f', '#f28e2b']


def layout(nodes, tot):
    total = sum(tot[n] for n in nodes)
    span = 10.0 - GAP * (len(nodes) - 1)
    pos, y = {}, 0.0
    for n in nodes:
        h = span * tot[n] / total
        pos[n] = (y, y + h)
        y += h + GAP
    return pos


def main():
    flows = sorted(json.load(open(LIN))['flows'], key=lambda f: -f['count'])
    owner = lambda r: r.split('/')[0]
    srcs, dsts = [], []
    out_tot, in_tot = defaultdict(int), defaultdict(int)
    for f in flows:
        if f['from'] not in srcs: srcs.append(f['from'])
        if f['to'] not in dsts: dsts.append(f['to'])
        out_tot[f['from']] += f['count']; in_tot[f['to']] += f['count']
    srcs.sort(key=lambda r: -out_tot[r]); dsts.sort(key=lambda r: -in_tot[r])
    Lp, Rp = layout(srcs, out_tot), layout(dsts, in_tot)

    fig, ax = plt.subplots(figsize=(15, 8.6))
    fig.set_facecolor('#f9f8f6'); ax.set_facecolor('#f9f8f6')
    xL, xR, bw = 0.0, 8.0, 0.34
    scol = {r: PAL[i % len(PAL)] for i, r in enumerate(srcs)}

    def band(y0a, y0b, y1a, y1b, color):
        x0, x1 = xL + bw, xR; mid = (x0 + x1) / 2
        v = [(x0, y0a), (mid, y0a), (mid, y1a), (x1, y1a),
             (x1, y1b), (mid, y1b), (mid, y0b), (x0, y0b), (x0, y0a)]
        c = [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4,
             MPath.LINETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.CLOSEPOLY]
        ax.add_patch(mp.PathPatch(MPath(v, c), fc=color, ec='none', alpha=0.45))

    loff = {n: Lp[n][0] for n in srcs}; roff = {n: Rp[n][0] for n in dsts}
    for f in flows:
        s, t, v = f['from'], f['to'], f['count']
        sh = (Lp[s][1] - Lp[s][0]) * v / out_tot[s]
        th = (Rp[t][1] - Rp[t][0]) * v / in_tot[t]
        y0a, y1a = loff[s], roff[t]; loff[s] += sh; roff[t] += th
        band(y0a, y0a + sh, y1a, y1a + th, scol[s])
    for n in srcs:
        a, b = Lp[n]; ax.add_patch(mp.Rectangle((xL, a), bw, b - a, fc=scol[n], ec='white'))
        ax.text(xL - 0.12, (a + b) / 2, f'{owner(n)} ({out_tot[n]})  ',
                ha='right', va='center', fontsize=11.5, family='monospace', weight='bold', color='#111')
    for n in dsts:
        a, b = Rp[n]; ax.add_patch(mp.Rectangle((xR, a), bw, b - a, fc='#8a8a8a', ec='white'))
        ax.text(xR + bw + 0.12, (a + b) / 2, f'  {owner(n)} ({in_tot[n]})',
                ha='left', va='center', fontsize=11.5, family='monospace', color='#111')
    ax.set_xlim(-3.6, xR + 3.8); ax.set_ylim(-0.6, 10.4); ax.axis('off')
    ax.set_title('Skill Lineage — direction-reliable copy flows   '
                 '(ancestor → descendant, band width = # skills copied)',
                 fontsize=13.5, family='monospace', color='#111', pad=16)
    ax.text(-3.6, -0.55,
            'Left = where skills were first authored (owner + #skills sent).  Right = repos that copied them.  '
            'Only trustworthy-direction flows shown\n(canonical authority + clean commit dates).  The big '
            'BbgnsurfTech↔davila7 batch is omitted — both bulk-published, so direction is unprovable.',
            fontsize=8.5, family='monospace', color='#5a5850')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(); plt.savefig(OUT, dpi=150, facecolor='#f9f8f6')
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
