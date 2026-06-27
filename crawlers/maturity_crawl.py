"""
maturity_crawl.py — Fetch per-skill git maturity and correlate with quality.

Answers: "do more-iterated skills have better definitions?" The main crawl
captured no git history, so this pass fetches, for each SKILL.md, its commit
count and first/last commit date via the GitHub commits API (?path=<file>),
then correlates that against the heuristic quality score.

Per-file commit count is the best available maturity proxy (how much a skill has
actually been worked on), unlike repo-level stars/recency which the study already
showed do NOT predict quality.

Usage:
    python crawlers/maturity_crawl.py --repos anthropics/skills,openai/skills
    python crawlers/maturity_crawl.py --all          # every repo (slow, 1 call/skill)
    python crawlers/maturity_crawl.py --token $GITHUB_TOKEN   # higher rate limit
"""
import argparse
import json
import os
import urllib.request
import urllib.error
import statistics as st
from pathlib import Path

BASE = Path(__file__).parent.parent
CRAWL = BASE / 'crawls' / 'crawl-1-2026-06-24' / 'data.json'
SCORES = BASE / 'data' / 'skill_quality.json'
OUT = BASE / 'data' / 'skill_maturity.json'


def gh(url, token):
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'skill-map',
        **({'Authorization': f'Bearer {token}'} if token else {})})
    return urllib.request.urlopen(req, timeout=40)


def commit_stats(repo, path, token):
    """commit count (via Link header) + first/last dates for one file path."""
    owner, name = repo.split('/', 1)
    base = (f'https://api.github.com/repos/{owner}/{name}/commits'
            f'?path={urllib.parse.quote(path)}&per_page=1')
    try:
        r = gh(base, token)
        data = json.loads(r.read())
        if not data:
            return None
        last_date = data[0]['commit']['committer']['date']
        # total count from the Link rel="last" header
        link = r.headers.get('Link', '')
        count = 1
        m = [p for p in link.split(',') if 'rel="last"' in p]
        if m:
            import re
            mm = re.search(r'[?&]page=(\d+)', m[0])
            if mm:
                count = int(mm.group(1))
        # first commit date = oldest page
        first_date = last_date
        if count > 1:
            r2 = gh(base + f'&page={count}', token)
            d2 = json.loads(r2.read())
            if d2:
                first_date = d2[-1]['commit']['committer']['date']
        return {'commits': count, 'first': first_date, 'last': last_date}
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError):
        return None


def corr(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** .5
    dy = sum((y - my) ** 2 for y in ys) ** .5
    return round(num / (dx * dy), 3) if dx * dy else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repos', help='comma-separated owner/repo list')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--token', default=os.environ.get('GITHUB_TOKEN'))
    ap.add_argument('--limit', type=int, help='max skills per repo')
    args = ap.parse_args()

    scores = json.load(open(SCORES))
    qbypath = {(s['repo'], s['file_path']): s['overall'] for s in scores['skills']}
    crawl = json.load(open(CRAWL))['results']

    want = None
    if args.repos:
        want = set(args.repos.split(','))
    targets = [r for r in crawl if r.get('skill_md_content')
               and (args.all or (want and r['repo_full_name'] in want))]
    if not targets:
        print('no targets — pass --repos or --all'); return

    rows = []
    by_repo = {}
    for r in targets:
        repo, path = r['repo_full_name'], r['file_path']
        by_repo.setdefault(repo, 0)
        if args.limit and by_repo[repo] >= args.limit:
            continue
        by_repo[repo] += 1
        cs = commit_stats(repo, path, args.token)
        if not cs:
            continue
        q = qbypath.get((repo, path))
        rows.append({'repo': repo, 'path': path, 'quality': q, **cs})
        print(f'  {repo[:24]:24s} {path.split("/")[-2][:22]:22s} '
              f'commits={cs["commits"]:3d} q={q}')

    if rows:
        commits = [r['commits'] for r in rows]
        qual = [r['quality'] for r in rows]
        med = st.median(commits)
        lo = [r['quality'] for r in rows if r['commits'] <= med]
        hi = [r['quality'] for r in rows if r['commits'] > med]
        summary = {
            'n': len(rows),
            'corr_commits_vs_quality': corr(commits, qual),
            'median_commits': med,
            'quality_of_low_commit': round(st.mean(lo), 1) if lo else None,
            'quality_of_high_commit': round(st.mean(hi), 1) if hi else None,
        }
        # Bulk-publish detection: skills aren't iterated in the repo if they
        # have a single commit, or if most share one first-commit day (a batch
        # "add skills" import). Either way, repo commit history measures
        # publishing, not development.
        per_repo = {}
        from collections import Counter, defaultdict
        byrepo = defaultdict(list)
        for r in rows:
            byrepo[r['repo']].append(r)
        for rp, rr in byrepo.items():
            day = Counter(r['first'][:10] for r in rr)
            top_day, top_n = day.most_common(1)[0]
            single = sum(1 for r in rr if r['commits'] == 1)
            per_repo[rp] = {
                'n': len(rr),
                'pct_single_commit': round(100 * single / len(rr)),
                'top_first_commit_day': top_day,
                'pct_on_top_day': round(100 * top_n / len(rr)),
                'median_commits': st.median([r['commits'] for r in rr]),
                'bulk_published': (single / len(rr) > 0.5) or (top_n / len(rr) > 0.6),
            }
        summary['bulk_publish_by_repo'] = per_repo
        OUT.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1))
        print('\nSUMMARY:', json.dumps(summary, indent=1))
        print(f'wrote {OUT}')


if __name__ == '__main__':
    import urllib.parse  # noqa
    main()
