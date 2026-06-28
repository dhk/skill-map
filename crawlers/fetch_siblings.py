"""
fetch_siblings.py — Backfill each skill's sibling files (the crawl only captured
SKILL.md, which blinded the progressive-disclosure axis to reference/ & scripts/).

For every repo in the merged corpus, fetch the git tree once (recursive) and, for
each SKILL.md, record the other files in its folder (one level into common
subdirs). Writes a sidecar data/sibling_files.json keyed by "repo\\tfile_path".

This is cheap (~1 trees call per repo) and the disclosure axis reads the sidecar,
so we never rewrite the big crawl data.json.

Usage:  python crawlers/fetch_siblings.py
"""
import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from score_corpus import load_all_crawls

BASE = Path(__file__).parent.parent
OUT = BASE / 'data' / 'sibling_files.json'


def gh(url):
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'skill-map'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def tree_paths(repo):
    # REVIEW(duplicate work + unauth): this re-fetches the SAME recursive tree that
    # crawl.py.walk_repo_tree already walked — just over the unauthenticated API
    # (60 req/hr; the bare except in main() turns rate-limit/404 into a skipped
    # repo and a blinded disclosure axis). If the crawl stored the per-repo blob
    # list (it has it in hand), this entire script + its network pass go away. It
    # also IGNORES the truncation flag (`t['truncated']`), so huge repos lose
    # sibling files silently — same latent bug as the crawl's tree walk.
    owner, name = repo.split('/', 1)
    info = gh(f'https://api.github.com/repos/{owner}/{name}')
    branch = info.get('default_branch', 'main')
    t = gh(f'https://api.github.com/repos/{owner}/{name}/git/trees/{branch}?recursive=1')
    return [n['path'] for n in t.get('tree', []) if n['type'] == 'blob']


def main():
    res = load_all_crawls()
    skills_by_repo = defaultdict(list)
    for x in res:
        if x.get('skill_md_content'):
            skills_by_repo[x['repo_full_name']].append(x['file_path'])

    out = {}
    for i, (repo, paths) in enumerate(sorted(skills_by_repo.items()), 1):
        try:
            allp = tree_paths(repo)
        except Exception as e:
            print(f'  [{i}/{len(skills_by_repo)}] {repo}: tree error {e.__class__.__name__}')
            continue
        for sp in paths:
            d = '/'.join(sp.replace('\\', '/').split('/')[:-1])
            sibs = [p for p in allp
                    if p != sp and (p.startswith(d + '/') if d else '/' not in p)]
            # keep folder-local + shallow; cap to avoid huge lists
            out[f'{repo}\t{sp}'] = sibs[:60]
        print(f'  [{i}/{len(skills_by_repo)}] {repo}: {len(paths)} skills, '
              f'{len(allp)} files in tree')
    OUT.write_text(json.dumps(out, indent=0))
    print(f'wrote {OUT} ({len(out)} skills annotated)')


if __name__ == '__main__':
    main()
