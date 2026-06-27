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
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent.parent
CRAWL = BASE / 'crawls' / 'crawl-1-2026-06-24' / 'data.json'
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
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'skill-map'})
    return urllib.request.urlopen(req, timeout=40)


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

    crawl = json.load(open(CRAWL))['results']
    skills = [x for x in crawl if x.get('skill_md_content')]
    scores = json.load(open(SCORES))
    qual = {(s['repo'], s['file_path']): s['overall'] for s in scores['skills']}
    stars = {rn: r['stars'] for rn, r in scores['repos'].items()}

    clusters = cluster(skills)
    print(f'{len(clusters)} cross-repo (near-)duplicate clusters, '
          f'{sum(len(c) for c in clusters)} skills')

    cache = json.load(open(DATES)) if DATES.exists() else {}
    out_clusters = []
    flows = defaultdict(int)
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
        dated = [m for m in members if m['first_date']]
        ancestor = min(dated, key=lambda m: m['first_date']) if dated else None
        _sp = c[0]['path'].replace('\\', '/').split('/')
        skill_name = _sp[-2] if len(_sp) >= 2 else _sp[-1]
        out_clusters.append({'skill': skill_name, 'n_repos': len({m['repo'] for m in members}),
                             'members': members, 'ancestor': ancestor})
        if ancestor:
            for m in members:
                if m['repo'] != ancestor['repo']:
                    flows[(ancestor['repo'], m['repo'])] += 1

    if not args.no_fetch:
        DATES.write_text(json.dumps(cache, indent=0))

    # non-obvious ancestors: small origin, big descendant
    nonobvious = []
    for c in out_clusters:
        a = c['ancestor']
        if not a or a['stars'] is None:
            continue
        desc_stars = [m['stars'] for m in c['members']
                      if m['repo'] != a['repo'] and m['stars'] is not None]
        if desc_stars and a['stars'] < 2000 and max(desc_stars) > 10 * max(1, a['stars']):
            nonobvious.append({'skill': c['skill'], 'ancestor_repo': a['repo'],
                               'ancestor_stars': a['stars'],
                               'ancestor_date': a['first_date'],
                               'biggest_descendant': max(
                                   (m for m in c['members'] if m['repo'] != a['repo']),
                                   key=lambda m: m['stars'] or 0)['repo'],
                               'descendant_stars': max(desc_stars)})
    nonobvious.sort(key=lambda x: -x['descendant_stars'])

    result = {'clusters': out_clusters,
              'flows': [{'from': k[0], 'to': k[1], 'count': v}
                        for k, v in sorted(flows.items(), key=lambda x: -x[1])],
              'nonobvious': nonobvious}
    OUT.write_text(json.dumps(result, indent=1))
    print(f'wrote {OUT}: {len(out_clusters)} clusters, '
          f'{len(result["flows"])} repo->repo flows, '
          f'{len(nonobvious)} non-obvious ancestors')
    for n in nonobvious[:8]:
        print(f"  NON-OBVIOUS: '{n['skill']}' originated in {n['ancestor_repo']} "
              f"({n['ancestor_stars']}*) -> copied into {n['biggest_descendant']} "
              f"({n['descendant_stars']}*)")


if __name__ == '__main__':
    main()
