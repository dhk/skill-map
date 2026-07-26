"""
vet_corpus_contributors.py — Flag suspicious new org entries added to
data/graph_data_v2.json in a PR, so a spam/backlink submission can't land on
a single quick review again.

Background: PR #1 ("Sync Xquik skills in map data", merged 2026-06-24) added
an org and two skill nodes for a Twitter/X scraping-and-automation product
with clear mass-produced-promotion signals: a submitting account with 5,056
public repos; a two-month-old org that shipped 11 language SDKs within a
34-minute window; every one of its repo descriptions carrying a "Not
affiliated with X Corp" disclaimer. Nothing caught it at merge time, because
no check ran at all on PRs touching data files outside SKILL.md — the diff
itself was two inert JSON records, which is exactly what made it look
trivial enough to wave through.

This script re-derives the signals that would have made a reviewer pause,
and prints them so a PR comment can surface them before the merge button
gets clicked. None of these prove bad faith on their own — a genuinely new,
small, legitimate org can trip one signal easily. They're meant to make a
human look twice, not to auto-block.

Usage:
    python crawlers/vet_corpus_contributors.py --base origin/main [--author LOGIN] [--strict]

Exit code is 0 (advisory) unless --strict is passed AND some new org
accumulates >= FAIL_THRESHOLD signals, in which case it exits 1.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ghapi import gh_json, has_token

GRAPH = Path(__file__).parent.parent / 'data' / 'graph_data_v2.json'

FAIL_THRESHOLD = 2       # signals needed to fail --strict mode
BURST_WINDOW_SECONDS = 3600  # repos created within this span of each other count as a "burst"
BURST_MIN_REPOS = 5      # this many (or more) repos in the window is suspicious
REPO_COUNT_FLAG = 1000   # author/org public_repos above this is a red flag
ORG_AGE_DAYS_FLAG = 120  # org younger than this is a red flag
DISCLAIMER_MIN_HITS = 3  # this many repos sharing a "not affiliated" disclaimer is a red flag


def load_graph_at(ref):
    if ref == 'WORKTREE':
        return json.loads(GRAPH.read_text())
    out = subprocess.run(['git', 'show', f'{ref}:data/graph_data_v2.json'],
                          capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def org_ids(graph):
    return {n['id'] for n in graph['nodes'] if n.get('type') == 'org'}


def new_org_logins(base_ref):
    base = org_ids(load_graph_at(base_ref))
    head = org_ids(load_graph_at('WORKTREE'))
    # ids look like "org:Xquik-dev"
    return [oid.split(':', 1)[1] for oid in (head - base)]


def _age_days(iso_ts):
    created = datetime.fromisoformat(iso_ts.replace('Z', '+00:00'))
    return (datetime.now(timezone.utc) - created).days


def check_org(login):
    """Return a list of red-flag strings for this org."""
    signals = []
    try:
        org = gh_json(f'https://api.github.com/orgs/{login}')
    except Exception as e:
        return [f'could not fetch org {login} from GitHub API: {e}']

    age_days = _age_days(org['created_at'])
    if age_days < ORG_AGE_DAYS_FLAG:
        signals.append(f'org created only {age_days}d ago (< {ORG_AGE_DAYS_FLAG}d)')

    if org.get('public_repos', 0) > REPO_COUNT_FLAG:
        signals.append(f'org has {org["public_repos"]} public repos')

    try:
        repos = gh_json(f'https://api.github.com/orgs/{login}/repos?per_page=100')
    except Exception:
        repos = []

    if repos:
        times = sorted(datetime.fromisoformat(r['created_at'].replace('Z', '+00:00')) for r in repos)
        for i, t in enumerate(times):
            window = [x for x in times if 0 <= (x - t).total_seconds() <= BURST_WINDOW_SECONDS]
            if len(window) >= BURST_MIN_REPOS:
                signals.append(f'{len(window)} repos created within '
                                f'{BURST_WINDOW_SECONDS // 60} minutes of each other')
                break

        descs = [(r.get('description') or '').lower() for r in repos]
        disclaimer_hits = sum(1 for d in descs if 'not affiliated' in d)
        if disclaimer_hits >= DISCLAIMER_MIN_HITS:
            signals.append(f'{disclaimer_hits} repo descriptions repeat the same '
                            f'"not affiliated with ..." disclaimer verbatim')

    return signals


def check_author(login):
    if not login:
        return []
    try:
        user = gh_json(f'https://api.github.com/users/{login}')
    except Exception as e:
        return [f'could not fetch author {login} from GitHub API: {e}']
    signals = []
    if user.get('public_repos', 0) > REPO_COUNT_FLAG:
        signals.append(f'PR author has {user["public_repos"]} public repos')
    return signals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='origin/main',
                     help='git ref to diff new org nodes against')
    ap.add_argument('--author', default=None,
                     help='GitHub login of the PR author, if known')
    ap.add_argument('--strict', action='store_true',
                     help='exit 1 if any entry accumulates >= %d signals' % FAIL_THRESHOLD)
    args = ap.parse_args()

    if not has_token():
        print('note: no GITHUB_TOKEN set — using the unauthenticated (60 req/hr) rate limit')

    new_orgs = new_org_logins(args.base)
    if not new_orgs and not args.author:
        print('no new org nodes in data/graph_data_v2.json — nothing to vet')
        return 0

    worst = 0
    for login in new_orgs:
        print(f'\n== new org: {login} ==')
        signals = check_org(login)
        if not signals:
            print('  no red flags')
        for s in signals:
            print(f'  ⚠️  {s}')
        worst = max(worst, len(signals))

    if args.author:
        print(f'\n== PR author: {args.author} ==')
        author_signals = check_author(args.author)
        if not author_signals:
            print('  no red flags')
        for s in author_signals:
            print(f'  ⚠️  {s}')
        worst = max(worst, len(author_signals))

    print()
    if args.strict and worst >= FAIL_THRESHOLD:
        print(f'FAIL: an entry accumulated {worst} signal(s) (>= {FAIL_THRESHOLD}) — '
              f'needs explicit human review before merging, not a quick approve.')
        return 1

    print('Advisory only — read the signals above (if any) before merging.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
