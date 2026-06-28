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
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from score_corpus import load_all_crawls
from ghapi import gh_json   # authenticated GitHub GET (5,000 req/hr vs 60)


def gh(url):
    return gh_json(url, timeout=60)


BASE = Path(__file__).parent.parent
OUT = BASE / 'data' / 'sibling_files.json'


def _blobs_bfs(owner, name, sha):
    """Per-directory walk for truncated trees (no flat 100k cap). Bounded."""
    out, stack, walked = [], [('', sha)], 0
    while stack and walked < 20000:
        prefix, s = stack.pop()
        try:
            t = gh(f'https://api.github.com/repos/{owner}/{name}/git/trees/{s}')
        except Exception:
            continue
        walked += 1
        for n in t.get('tree', []):
            full = f"{prefix}{n['path']}"
            if n['type'] == 'tree':
                stack.append((full + '/', n['sha']))
            elif n['type'] == 'blob':
                out.append(full)
    return out


def tree_paths(repo):
    # LEGACY FALLBACK only: crawl.py now captures sibling_files during its
    # authenticated tree walk and main() prefers those, so this re-fetch runs only
    # for repos crawled before that change.
    owner, name = repo.split('/', 1)
    info = gh(f'https://api.github.com/repos/{owner}/{name}')
    branch = info.get('default_branch', 'main')
    t = gh(f'https://api.github.com/repos/{owner}/{name}/git/trees/{branch}?recursive=1')
    if t.get('truncated'):
        # Recover the full list per-directory instead of losing files past the cut.
        print(f'    {repo}: tree truncated — walking per-directory')
        return _blobs_bfs(owner, name, t['sha'])
    return [n['path'] for n in t.get('tree', []) if n['type'] == 'blob']


def main():
    res = load_all_crawls()

    # FAST PATH: harvest siblings the crawl already captured (crawl.py now stores
    # `sibling_files` per skill from the tree it walked). Anything covered here
    # needs no network call at all.
    out = {}
    skills_by_repo = defaultdict(list)
    for x in res:
        if not x.get('skill_md_content'):
            continue
        key = f"{x['repo_full_name']}\t{x['file_path']}"
        sib = x.get('sibling_files')
        if sib is not None:                       # present (incl. []) → trust crawl
            out[key] = sib[:60]
        else:                                     # older crawl: needs API backfill
            skills_by_repo[x['repo_full_name']].append(x['file_path'])

    from_crawl = len(out)
    print(f'{from_crawl} skills annotated from crawl snapshots (no network); '
          f'{len(skills_by_repo)} repos need API backfill')

    # SLOW PATH (legacy): only repos whose crawl predates sibling capture.
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
    print(f'wrote {OUT} ({len(out)} skills annotated; {from_crawl} from crawl, '
          f'{len(out) - from_crawl} from API)')


if __name__ == '__main__':
    main()
