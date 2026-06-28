"""
track_history.py — Incremental crawl state + change detection.

Ingests every crawl snapshot in order and maintains data/skill_history.json: a
per-skill timeline (first seen, last seen, SHA history, quality history) plus a
per-crawl delta (what was added / changed / removed / re-scored).

Change detection is scoped per repo: a re-crawl only marks skills "removed" for
repos it actually re-observed, so disjoint crawls (e.g. crawl-2 adding brand-new
repos) don't false-flag crawl-1's skills as gone.

Outputs:
  data/skill_history.json   running state + deltas
  prints the latest delta (the changelog)

Usage:  python crawlers/track_history.py
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from skill_quality import score_skill

BASE = Path(__file__).parent.parent
CRAWLS = BASE / 'crawls'
OUT = BASE / 'data' / 'skill_history.json'


def crawl_results(data_path):
    return [r for r in json.load(open(data_path)).get('results', [])
            if r.get('skill_md_content')]


def main():
    crawl_dirs = sorted(d for d in CRAWLS.glob('*/data.json'))
    hist = {'crawls': [], 'skills': {}, 'deltas': {}}
    seen_repos = set()
    # per-repo last-known live skill keys (for removal detection)
    live_by_repo = defaultdict(set)

    for data_path in crawl_dirs:
        crawl_id = data_path.parent.name
        rows = crawl_results(data_path)
        repos_here = {r['repo_full_name'] for r in rows}
        cur = {}                       # (repo,path) -> row
        for r in rows:
            cur[(r['repo_full_name'], r['file_path'])] = r

        added, changed, removed, movers = [], [], [], []
        for (repo, path), r in cur.items():
            key = f'{repo}\t{path}'
            sha = r.get('file_sha')
            dir_name = path.replace('\\', '/').split('/')[-2] if '/' in path else None
            # REVIEW(inconsistency): scores here WITHOUT sibling_files, while
            # score_corpus.py scores the same skills WITH data/sibling_files.json.
            # The disclosure axis credits reference/scripts siblings, so a skill's
            # "quality" in skill_history.json can differ from its quality in
            # skill_quality.json / STATS.md — and the history "top movers" can show
            # a score delta that is really just the siblings sidecar appearing,
            # not the skill changing. Pass the same siblings here for one number.
            score = score_skill(r['skill_md_content'], dir_name)['overall']
            words = len(r['skill_md_content'].split())
            if key not in hist['skills']:
                added.append(key)
                hist['skills'][key] = {
                    'first_seen': crawl_id, 'last_seen': crawl_id,
                    'name': dir_name, 'repo': repo, 'shas': [sha],
                    'quality': [{'crawl': crawl_id, 'score': score}],
                    'words': [{'crawl': crawl_id, 'n': words}]}
            else:
                h = hist['skills'][key]
                h['last_seen'] = crawl_id
                if sha and sha != h['shas'][-1]:
                    h['shas'].append(sha)
                    prev = h['quality'][-1]['score']
                    prev_w = h.get('words', [{'n': words}])[-1]['n']
                    h['quality'].append({'crawl': crawl_id, 'score': score})
                    h.setdefault('words', []).append({'crawl': crawl_id, 'n': words})
                    changed.append(key)
                    movers.append((key, round(score - prev, 1), words - prev_w))

        # removal: only for repos this crawl actually re-observed
        for repo in repos_here:
            prior = live_by_repo[repo]
            now = {f'{repo}\t{p}' for (rp, p) in cur if rp == repo}
            for key in prior - now:
                removed.append(key)
            live_by_repo[repo] = now

        movers.sort(key=lambda x: -max(abs(x[1]), abs(x[2]) / 100))
        delta = {
            'skills_added': len(added),
            'skills_changed': len(changed),
            'skills_removed': len(removed),
            'repos_added': sorted(repos_here - seen_repos),
            'top_movers': movers[:15],
            'sample_added': added[:15],
        }
        hist['crawls'].append(crawl_id)
        hist['deltas'][crawl_id] = delta
        seen_repos |= repos_here

    OUT.write_text(json.dumps(hist, indent=1))
    latest = hist['crawls'][-1]
    d = hist['deltas'][latest]
    print(f'history → {OUT}  ({len(hist["skills"])} skills tracked across '
          f'{len(hist["crawls"])} crawls)')
    print(f'\nlatest delta — {latest}:')
    print(f'  +{d["skills_added"]} added, ~{d["skills_changed"]} changed, '
          f'-{d["skills_removed"]} removed')
    if d['repos_added']:
        print(f'  new repos: {", ".join(d["repos_added"])}')
    if d['top_movers']:
        print('  biggest movers (quality Δ, words Δ):')
        for key, dv, dw in d['top_movers'][:8]:
            print(f'    score {dv:+5.1f}  words {dw:+6d}  {key.replace(chr(9), " / ")}')


if __name__ == '__main__':
    main()
