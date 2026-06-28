"""
check_docs.py — Flag headline numbers in the narrative docs that disagree with
the live corpus (data/corpus_stats.json). It does NOT auto-edit prose (too
fragile); it warns, so drift is caught instead of silently shipped.

Checks the load-bearing figures: skill count, repo count, median quality,
WHEN-trigger %. Ignores numbers inside explicit "Correction"/"Update"/historical
blockquotes (they intentionally cite old values).

Usage:  python crawlers/check_docs.py      # exit 1 if any doc is stale
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
STATS = BASE / 'data' / 'corpus_stats.json'
DOCS = BASE / 'docs'


def main():
    if not STATS.exists():
        print('no corpus_stats.json — run gen_stats.py first'); return 0
    s = json.load(open(STATS))
    n_skills, n_repos = s['n_skills'], s['n_repos']
    median, when = s['median_quality'], s['pct_with_when']

    # REVIEW(self-defeating): the stale values to hunt for are themselves hard-coded
    # (73.5, 4,902, 5,320, "only 43%", "39 repos"...). This is the one drift the
    # guard cannot catch automatically: when the LIVE numbers move to a new value,
    # someone must hand-add the previous live number to this list or the next round
    # of staleness ships unflagged. Consider flagging any "<n> skills / <n> repos"
    # figure that doesn't match the live stats, rather than enumerating known-bad
    # constants.
    # current values that should appear; flag well-known *stale* alternates only
    # when they show up outside historical/correction context.
    stale_patterns = [
        (re.compile(r'\b(73\.5|79\.5|79\.8|76\.2)\s*/?\s*100|\bmedian (?:quality )?(?:of )?(73\.5|79\.5|79\.8|76\.2)\b'),
         f'median quality (live: {median})'),
        (re.compile(r'\b(4,902|4,900|5,320)\s+(?:crawled\s+)?skills?\b|\b(39|40)\s+repos\b'),
         f'corpus size (live: {n_skills:,} skills / {n_repos} repos)'),
        (re.compile(r'\bonly\s+43%\b'), f'WHEN-trigger rate (live: {when}%)'),
    ]
    hist_ctx = re.compile(r'correction|earlier pass|first reported|update \(|historical|was reported|crawl-\d+-\d|^>',
                          re.I)

    issues = []
    for md in sorted(DOCS.glob('*.md')):
        if md.name in ('STATS.md',):
            continue
        for i, line in enumerate(md.read_text().splitlines(), 1):
            if hist_ctx.search(line):
                continue
            for pat, label in stale_patterns:
                if pat.search(line):
                    issues.append((md.name, i, label, line.strip()[:90]))

    if not issues:
        print(f'docs consistent with live corpus '
              f'({n_skills:,} skills, {n_repos} repos, median {median}, WHEN {when}%)')
        return 0
    print(f'⚠️  {len(issues)} possibly-stale figure(s) (vs live corpus):')
    for name, ln, label, text in issues:
        print(f'  {name}:{ln}  [{label}]  {text}')
    return 1


if __name__ == '__main__':
    sys.exit(main())
