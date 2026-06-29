"""
lineage_trace.py — Trace the lineage of copied skills across the corpus.

The bulk-publish finding showed the mega-collections are largely copied. This
asks: copied *from where*? It clusters near-identical skills across repos, then
uses each copy's first-commit date (GitHub commits API) to find the **ancestor**
— the repo where the skill appeared earliest — and the descendants that copied it.

Outputs data/lineage.json:
  clusters    [{skill, members:[{repo,path,first_date,stars,quality}], ancestor}]
  flows       repo -> repo copy counts (for a Sankey)
  nonobvious  clusters whose ancestor is a SMALL/unknown repo that propagated
              into far bigger ones — the good origin stories

Usage:
    python crawlers/lineage_trace.py            # cluster + fetch dates + write
    python crawlers/lineage_trace.py --no-fetch # cluster only (skip API)
"""
import argparse
import json
import re
import sys
import hashlib
import urllib.parse
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent))
from score_corpus import load_all_crawls   # canonical merged-corpus loader
from ghapi import gh_get                    # authenticated GitHub GET

BASE = Path(__file__).parent.parent
# Clusters over the MERGED corpus (all crawls), so skills that first appear in a
# later crawl are included in the copy/ancestry analysis. Lineage runs in the
# pipeline and feeds originator_leaderboard, curiosities, and both figures.
SCORES = BASE / 'data' / 'skill_quality.json'
DATES = BASE / 'data' / 'commit_dates.json'
OUT = BASE / 'data' / 'lineage.json'

STOP = {'skill', 'using', 'with', 'for', 'the', 'and', 'pro', 'advanced'}


def norm_body(md):
    m = re.match(r'^\s*---\s*\n.*?\n---\s*\n?(.*)$', md, re.S)
    body = (m.group(1) if m else md).lower()
    return re.sub(r'\s+', ' ', body).strip()


def concept(name):
    toks = [t for t in re.split(r'[-_\s]+', (name or '').lower())
            if t and t not in STOP]
    return ' '.join(sorted(toks))


def shingles(text, k=5):
    w = text.split()
    return {' '.join(w[i:i + k]) for i in range(max(1, len(w) - k + 1))}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster(skills):
    """Cluster cross-repo (near-)duplicates. Exact-body clusters, plus
    fuzzy clusters within a shared concept-name (catches edited copies)."""
    items = []
    for x in skills:
        body = norm_body(x['skill_md_content'])
        if len(body) < 80:
            continue
        _p = x['file_path'].replace('\\', '/').split('/')
        items.append({'repo': x['repo_full_name'], 'path': x['file_path'],
                      'concept': concept(_p[-2] if len(_p) >= 2 else _p[-1]),
                      'body': body,
                      'h': hashlib.sha1(body.encode()).hexdigest()})

    parent = {i: i for i in range(len(items))}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    # exact body matches
    by_hash = defaultdict(list)
    for i, it in enumerate(items):
        by_hash[it['h']].append(i)
    for idxs in by_hash.values():
        for j in idxs[1:]:
            union(idxs[0], j)

    # fuzzy within concept groups
    by_concept = defaultdict(list)
    for i, it in enumerate(items):
        if it['concept']:
            by_concept[it['concept']].append(i)
    for idxs in by_concept.values():
        if len(idxs) < 2:
            continue
        sh = {i: shingles(items[i]['body']) for i in idxs}
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                if find(i) == find(j):
                    continue
                if jaccard(sh[i], sh[j]) >= 0.8:
                    union(i, j)

    groups = defaultdict(list)
    for i in range(len(items)):
        groups[find(i)].append(i)

    clusters = []
    for idxs in groups.values():
        repos = {items[i]['repo'] for i in idxs}
        if len(repos) < 2:
            continue
        clusters.append([items[i] for i in idxs])
    return clusters


def gh(url):
    # Authenticated via $GITHUB_TOKEN (ghapi) — 5,000 req/hr vs 60 unauth — so the
    # per-file commit-date pass doesn't exhaust the limit and quietly drop dates.
    # (Capturing commit dates DURING the crawl would remove this pass entirely.)
    return gh_get(url)


def first_commit_date(repo, path, cache):
    key = f'{repo}\t{path}'
    if key in cache:
        return cache[key]
    owner, name = repo.split('/', 1)
    base = (f'https://api.github.com/repos/{owner}/{name}/commits'
            f'?path={urllib.parse.quote(path)}&per_page=1')
    date = None
    try:
        r = gh(base)
        data = json.loads(r.read())
        if data:
            date = data[0]['commit']['committer']['date']
            link = r.headers.get('Link', '')
            m = [p for p in link.split(',') if 'rel="last"' in p]
            if m:
                mm = re.search(r'[?&]page=(\d+)', m[0])
                if mm:
                    r2 = gh(base + f'&page={mm.group(1)}')
                    d2 = json.loads(r2.read())
                    if d2:
                        date = d2[-1]['commit']['committer']['date']
    except Exception:
        date = None
    cache[key] = date
    return date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-fetch', action='store_true')
    args = ap.parse_args()

    skills = [x for x in load_all_crawls() if x.get('skill_md_content')]
    scores = json.load(open(SCORES))
    qual = {(s['repo'], s['file_path']): s['overall'] for s in scores['skills']}
    stars = {rn: r['stars'] for rn, r in scores['repos'].items()}

    clusters = cluster(skills)
    print(f'{len(clusters)} cross-repo (near-)duplicate clusters, '
          f'{sum(len(c) for c in clusters)} skills')

    cache = json.load(open(DATES)) if DATES.exists() else {}

    # Pass 1: gather members + dates for every cluster.
    raw = []
    n_fetch = sum(len(c) for c in clusters)
    done = 0
    for c in clusters:
        members = []
        for it in c:
            date = None
            if not args.no_fetch:
                date = first_commit_date(it['repo'], it['path'], cache)
                done += 1
                if done % 50 == 0:
                    print(f'  fetched {done}/{n_fetch} commit dates')
            members.append({'repo': it['repo'], 'path': it['path'],
                            'first_date': date,
                            'stars': stars.get(it['repo']),
                            'quality': qual.get((it['repo'], it['path']))})
        _sp = c[0]['path'].replace('\\', '/').split('/')
        raw.append((_sp[-2] if len(_sp) >= 2 else _sp[-1], members))
    if not args.no_fetch:
        DATES.write_text(json.dumps(cache, indent=0))

    # Detect bulk-published repos: a repo whose skills mostly share ONE
    # first-commit day is a snapshot, so its commit DATES cannot be trusted as
    # authorship dates (the same effect that invalidated the maturity analysis).
    # Lineage *direction* through such a repo is unreliable.
    repo_days = defaultdict(list)
    for _, members in raw:
        for m in members:
            if m['first_date']:
                repo_days[m['repo']].append(m['first_date'][:10])
    bulk = set()
    for r, days in repo_days.items():
        if len(days) >= 3:
            if Counter(days).most_common(1)[0][1] / len(days) > 0.5:
                bulk.add(r)

    # Canonical authority prior: vendor repos are the origin of their own
    # skills regardless of when their public snapshot was committed.
    CANON = {'anthropics/skills', 'openai/skills'}

    def pick_ancestor(members):
        dated = [m for m in members if m['first_date']]
        if not dated:
            return None, 'no-dates'
        canon = [m for m in dated if m['repo'] in CANON]
        if canon:
            return min(canon, key=lambda m: m['first_date']), 'canonical-authority'
        earliest = min(dated, key=lambda m: m['first_date'])
        # direction is reliable only if the earliest repo isn't a snapshot
        reliable = earliest['repo'] not in bulk
        return earliest, ('date-reliable' if reliable else 'date-unreliable')

    out_clusters = []
    flows = defaultdict(int)
    for skill_name, members in raw:
        ancestor, basis = pick_ancestor(members)
        out_clusters.append({'skill': skill_name,
                             'n_repos': len({m['repo'] for m in members}),
                             'members': members, 'ancestor': ancestor,
                             'ancestor_basis': basis})
        # only count flows when we trust the direction
        if ancestor and basis in ('canonical-authority', 'date-reliable'):
            for m in members:
                if m['repo'] != ancestor['repo']:
                    flows[(ancestor['repo'], m['repo'])] += 1

    # Non-obvious ancestors — ONLY from reliable directions (small origin, big
    # descendant). The naive version was dominated by bulk-publish artifacts.
    nonobvious = []
    for c in out_clusters:
        a = c['ancestor']
        if not a or a['stars'] is None or c['ancestor_basis'] != 'date-reliable':
            continue
        desc = [m for m in c['members'] if m['repo'] != a['repo']
                and m['stars'] is not None]
        if desc and a['stars'] < 2000:
            big = max(desc, key=lambda m: m['stars'])
            if big['stars'] > 10 * max(1, a['stars']):
                nonobvious.append({'skill': c['skill'], 'ancestor_repo': a['repo'],
                                   'ancestor_stars': a['stars'],
                                   'ancestor_date': a['first_date'],
                                   'biggest_descendant': big['repo'],
                                   'descendant_stars': big['stars']})
    nonobvious.sort(key=lambda x: -x['descendant_stars'])

    basis_ct = Counter(c['ancestor_basis'] for c in out_clusters)
    result = {'clusters': out_clusters,
              'bulk_published_repos': sorted(bulk),
              'ancestor_basis_counts': dict(basis_ct),
              'flows': [{'from': k[0], 'to': k[1], 'count': v}
                        for k, v in sorted(flows.items(), key=lambda x: -x[1])],
              'nonobvious': nonobvious}
    OUT.write_text(json.dumps(result, indent=1))
    print(f'wrote {OUT}: {len(out_clusters)} clusters, '
          f'{len(result["flows"])} reliable repo->repo flows, '
          f'{len(nonobvious)} non-obvious ancestors (reliable only)')
    print(f'  bulk-published (date-unreliable) repos: {sorted(bulk)}')
    print(f'  ancestor basis: {dict(basis_ct)}')
    for n in nonobvious[:8]:
        print(f"  NON-OBVIOUS: '{n['skill']}' originated in {n['ancestor_repo']} "
              f"({n['ancestor_stars']}*) -> {n['biggest_descendant']} "
              f"({n['descendant_stars']}*)")


if __name__ == '__main__':
    main()
