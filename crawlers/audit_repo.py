"""
audit_repo.py — Audit any skills repo (local OR GitHub, public or private)
against the Anthropic gold standard, and recommend what to fix and what to add.

This is the "run it on your own repo" deliverable. It:
  1. collects every SKILL.md in the target (local glob or GitHub tree API),
  2. scores each with skill_quality + classifies the repo signature,
  3. benchmarks the repo against same-signature peers in the crawled corpus,
  4. prints a report: grade distribution, practices to adopt, the worst
     offenders to fix, and the top-N general-purpose skills the repo is
     missing (skills that are widely adopted AND high quality across the corpus).

Usage:
    # local
    python crawlers/audit_repo.py /path/to/repo
    python crawlers/audit_repo.py ~/.claude/skills

    # GitHub (public or private — token via --token or $GITHUB_TOKEN)
    python crawlers/audit_repo.py --github owner/repo
    python crawlers/audit_repo.py --github owner/repo --token ghp_xxx --branch main

    # machine-readable
    python crawlers/audit_repo.py /path/to/repo --json
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import statistics as st
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from skill_quality import score_skill
from repo_signature import classify_repo, SIGNATURE_GUIDANCE

BASE = Path(__file__).parent.parent
CORPUS = BASE / 'data' / 'skill_quality.json'

# Words stripped when normalising a skill name to a "concept" for the
# missing-skills recommender (so "pdf-generator" and "generate-pdf" collide).
STOP = {'skill', 'agent', 'claude', 'code', 'helper', 'tool', 'generator',
        'creator', 'builder', 'manager', 'create', 'generate', 'build',
        'using', 'with', 'for', 'the', 'a', 'an', 'and', 'to', 'of', 'pro',
        'advanced', 'simple', 'basic', 'custom', 'auto'}


def normalize_concept(name):
    toks = [t for t in re.split(r'[-_\s]+', (name or '').lower()) if t]
    toks = [t for t in toks if t not in STOP]
    return ' '.join(sorted(toks)) if toks else (name or '').lower()


# ── Collection ────────────────────────────────────────────────────────
def collect_local(root):
    root = Path(root).expanduser()
    out = []
    for p in root.rglob('SKILL.md'):
        out.append((str(p.relative_to(root)), p.read_text(errors='replace')))
    # also accept *.skill.md / skill.md casing
    for p in root.rglob('*.md'):
        if p.name.lower() == 'skill.md' and p.name != 'SKILL.md':
            out.append((str(p.relative_to(root)), p.read_text(errors='replace')))
    return out


def _gh(url, token):
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'skill-map-auditor',
        **({'Authorization': f'Bearer {token}'} if token else {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def collect_github(slug, token, branch=None):
    owner, repo = slug.split('/', 1)
    if not branch:
        info = _gh(f'https://api.github.com/repos/{owner}/{repo}', token)
        branch = info.get('default_branch', 'main')
    tree = _gh(f'https://api.github.com/repos/{owner}/{repo}/git/trees/'
               f'{branch}?recursive=1', token)
    out = []
    for node in tree.get('tree', []):
        if node['type'] == 'blob' and node['path'].split('/')[-1] == 'SKILL.md':
            raw = (f'https://raw.githubusercontent.com/{owner}/{repo}/'
                   f'{branch}/{node["path"]}')
            req = urllib.request.Request(raw, headers={
                'User-Agent': 'skill-map-auditor',
                **({'Authorization': f'Bearer {token}'} if token else {})})
            with urllib.request.urlopen(req, timeout=60) as r:
                out.append((node['path'], r.read().decode('utf-8', 'replace')))
    return out, branch


# ── Recommender ───────────────────────────────────────────────────────
def general_purpose_index(corpus, min_repos=4, min_quality=75):
    """Concepts that are widely adopted AND high quality across the corpus."""
    by_concept = defaultdict(lambda: {'repos': set(), 'scores': [], 'names': defaultdict(int)})
    for s in corpus['skills']:
        c = normalize_concept(s['name'])
        if not c:
            continue
        e = by_concept[c]
        e['repos'].add(s['repo'])
        e['scores'].append(s['overall'])
        e['names'][s['name']] += 1
    idx = {}
    for c, e in by_concept.items():
        if len(e['repos']) >= min_repos:
            med = st.median(e['scores'])
            if med >= min_quality:
                label = max(e['names'].items(), key=lambda x: x[1])[0]
                idx[c] = {'label': label, 'n_repos': len(e['repos']),
                          'median_quality': round(med, 1)}
    return idx


# ── Audit ─────────────────────────────────────────────────────────────
def _norm_body(md):
    m = re.match(r'^\s*---\s*\n.*?\n---\s*\n?(.*)$', md or '', re.S)
    return re.sub(r'\s+', ' ', (m.group(1) if m else (md or '')).lower()).strip()


def find_overlap(files):
    """Intra-repo near-duplicate skills — the checklist's 'doesn't overlap with
    another skill'. Returns clusters of >1 skill with near-identical bodies."""
    bodies = []
    for path, md in files:
        b = _norm_body(md)
        if len(b) >= 80:
            bodies.append((path, set(b.split())))
    clusters, used = [], set()
    for i in range(len(bodies)):
        if i in used:
            continue
        grp = [bodies[i][0]]
        for j in range(i + 1, len(bodies)):
            if j in used:
                continue
            a, b = bodies[i][1], bodies[j][1]
            if a and b and len(a & b) / len(a | b) >= 0.8:
                grp.append(bodies[j][0])
                used.add(j)
        if len(grp) > 1:
            clusters.append(grp)
    return clusters


def audit(files, owner_type='User', stars=None, source=None):
    scored = []
    for path, md in files:
        parts = path.replace('\\', '/').split('/')
        dir_name = parts[-2] if len(parts) >= 2 else None
        sc = score_skill(md, dir_name)
        scored.append({'path': path, 'name': sc['metrics']['name'] or dir_name,
                       'overall': sc['overall'], 'grade': sc['grade'],
                       'flags': sc['flags'], 'scores': sc['scores'],
                       'desc_has_when': sc['metrics']['desc_has_when'],
                       'ref_files': sc['metrics']['ref_files']})
    if not scored:
        return None
    ov = [s['overall'] for s in scored]
    med = st.median(ov)
    std = st.pstdev(ov) if len(ov) > 1 else 0.0
    sig = classify_repo({'n_skills': len(scored), 'owner_type': owner_type,
                         'stars': stars, 'median_quality': med,
                         'quality_stdev': std, 'source': source})
    flagct = defaultdict(int)
    for s in scored:
        for f in s['flags']:
            flagct[f] += 1
    gd = defaultdict(int)
    for s in scored:
        gd[s['grade']] += 1
    overlap = find_overlap(files)
    return {'n_skills': len(scored), 'median_quality': round(med, 1),
            'mean_quality': round(st.mean(ov), 1), 'quality_stdev': round(std, 1),
            'signature': sig['signature'], 'signature_rationale': sig['rationale'],
            'grade_dist': dict(sorted(gd.items())),
            'pct_with_when': round(100 * sum(s['desc_has_when'] for s in scored) / len(scored), 1),
            'pct_uses_refs': round(100 * sum(s['ref_files'] > 0 for s in scored) / len(scored), 1),
            'flag_freq': sorted(flagct.items(), key=lambda x: -x[1]),
            'overlap_clusters': overlap,
            'skills': scored}


def build_report(a, corpus, target_name, top_n=10):
    L = []
    sig = a['signature']
    peer = corpus['signatures'].get(sig, {})
    L.append(f'# Skill audit — {target_name}\n')
    L.append(f'**Signature:** `{sig}` — {a["signature_rationale"]}\n')
    L.append(f'**Skills:** {a["n_skills"]}  ·  '
             f'**Median quality:** {a["median_quality"]}/100  ·  '
             f'**WHEN-triggers:** {a["pct_with_when"]}%  ·  '
             f'**Uses reference files:** {a["pct_uses_refs"]}%\n')
    if peer:
        L.append(f'### Benchmark vs same-signature peers in the corpus\n')
        L.append(f'| metric | you | `{sig}` peers |')
        L.append('|---|---|---|')
        L.append(f'| median quality | {a["median_quality"]} | {peer["median_quality"]} |')
        L.append(f'| % with WHEN-trigger | {a["pct_with_when"]}% | {peer["pct_with_when"]}% |')
        L.append(f'| % uses reference files | {a["pct_uses_refs"]}% | {peer["pct_uses_refs"]}% |\n')
    L.append(f'**Grade distribution:** ' +
             '  '.join(f'{g}:{n}' for g, n in a['grade_dist'].items()) + '\n')

    # Practices to adopt
    g = SIGNATURE_GUIDANCE.get(sig, {})
    if g:
        L.append('## Practices to adopt\n')
        L.append(f'_{g["summary"]}_\n')
        for d in g['do']:
            L.append(f'- {d}')
        L.append('')
    # Flag-driven fixes
    if a['flag_freq']:
        L.append('## Most common issues (fix these first)\n')
        for f, n in a['flag_freq'][:6]:
            L.append(f'- **{f}** — {n} skill(s) ({round(100*n/a["n_skills"])}%)')
        L.append('')
    # Worst offenders
    worst = sorted(a['skills'], key=lambda s: s['overall'])[:8]
    L.append('## Worst offenders\n')
    L.append('| skill | score | grade | issues |')
    L.append('|---|---|---|---|')
    for s in worst:
        L.append(f'| `{s["name"]}` | {s["overall"]} | {s["grade"]} | '
                 f'{", ".join(s["flags"]) or "—"} |')
    L.append('')
    # Scope / overlap (the checklist's "doesn't overlap with another skill")
    ov = a.get('overlap_clusters') or []
    if ov:
        L.append('## Scope — overlapping skills (consolidate these)\n')
        L.append('_Near-identical skills within this repo. Each cluster is one job '
                 'split across multiple skills; merge or differentiate them._\n')
        for grp in ov[:8]:
            L.append(f'- { " ≈ ".join("`"+g.split("/")[-2]+"`" if "/" in g else "`"+g+"`" for g in grp) }')
        L.append('')

    # Checklist items the heuristic flags but a human should confirm
    of = sum(1 for s in a['skills'] if 'output-format-unstated' in s['flags'])
    hs = sum(1 for s in a['skills'] if 'high-stakes-no-safety' in s['flags'])
    if of or hs:
        L.append('## Checklist gaps (informational — confirm by reading)\n')
        if of:
            L.append(f'- **{of} skill(s)** never state their output format — '
                     'add an explicit "Output:" section where format matters.')
        if hs:
            L.append(f'- **{hs} skill(s)** describe high-stakes operations '
                     '(deploy/delete/payments/secrets) with **no visible validation, '
                     'dry-run, or guard step** — add safety scaffolding.')
        L.append('')

    # Missing general-purpose skills
    idx = general_purpose_index(corpus)
    have = {normalize_concept(s['name']) for s in a['skills']}
    missing = [(c, v) for c, v in idx.items() if c not in have]
    missing.sort(key=lambda x: (-x[1]['n_repos'], -x[1]['median_quality']))
    L.append(f'## Top {top_n} general-purpose skills you\'re missing\n')
    L.append('_Concepts that are widely adopted AND high quality across the '
             'crawled corpus, that this repo does not have._\n')
    L.append('| skill concept | adopted by N repos | median quality |')
    L.append('|---|---|---|')
    for c, v in missing[:top_n]:
        L.append(f'| {v["label"]} | {v["n_repos"]} | {v["median_quality"]} |')
    L.append('')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path', nargs='?', help='local repo path')
    ap.add_argument('--github', help='owner/repo')
    ap.add_argument('--token', default=os.environ.get('GITHUB_TOKEN'))
    ap.add_argument('--branch')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--top-n', type=int, default=10)
    ap.add_argument('--out', help='write report to file')
    args = ap.parse_args()

    if args.github:
        files, branch = collect_github(args.github, args.token, args.branch)
        target = f'{args.github}@{branch}'
        owner_type = 'Organization' if '/' in args.github else 'User'
    elif args.path:
        files = collect_local(args.path)
        target = args.path
        owner_type = 'User'
    else:
        ap.error('provide a local path or --github owner/repo')

    if not files:
        print('No SKILL.md files found.', file=sys.stderr)
        sys.exit(2)

    a = audit(files, owner_type=owner_type)
    corpus = json.load(open(CORPUS))
    if args.json:
        out = json.dumps(a, indent=1)
    else:
        out = build_report(a, corpus, target, top_n=args.top_n)
    if args.out:
        Path(args.out).write_text(out)
        print(f'wrote {args.out}')
    else:
        print(out)


if __name__ == '__main__':
    main()
