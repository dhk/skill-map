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

    # Curated stale-value patterns (kept for the specific phrasings that recur).
    stale_patterns = [
        (re.compile(r'\b(73\.5|79\.5|79\.8|76\.2)\s*/?\s*100|\bmedian (?:quality )?(?:of )?(73\.5|79\.5|79\.8|76\.2)\b'),
         f'median quality (live: {median})'),
        (re.compile(r'\bonly\s+43%\b'), f'WHEN-trigger rate (live: {when}%)'),
    ]
    hist_ctx = re.compile(r'correction|earlier pass|first reported|update \(|historical|was reported|crawl-\d+-\d|^>',
                          re.I)

    # GENERIC drift check: flag a stale corpus total WITHOUT hand-enumerating old
    # constants — but ONLY on lines phrased as the headline ("N skills across …",
    # "collected/​swept/​crawled N …"). That cue is what distinguishes the corpus
    # total from the many legitimate per-repo "66 skills" counts in the docs.
    def _num(s):
        return int(s.replace(',', ''))
    headline_cue = re.compile(r'across|collected|crawled|swept|sweep|corpus|in total|total of', re.I)
    skills_fig = re.compile(r'\b(\d[\d,]*)\s+(?:crawled\s+|published\s+|full\s+)?skills?\b', re.I)
    repos_fig = re.compile(r'\b(\d[\d,]*)\s+repos(?:itories)?\b', re.I)

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
            if not headline_cue.search(line):
                continue
            for m in skills_fig.finditer(line):
                # floor of 1,000 keeps sample sizes ("across 172 skills") from
                # masquerading as a stale corpus total.
                if _num(m.group(1)) >= 1000 and _num(m.group(1)) != n_skills:
                    issues.append((md.name, i,
                                   f'headline skill count {m.group(1)} (live: {n_skills:,})',
                                   line.strip()[:90]))
            for m in repos_fig.finditer(line):
                if _num(m.group(1)) != n_repos:
                    issues.append((md.name, i,
                                   f'headline repo count {m.group(1)} (live: {n_repos})',
                                   line.strip()[:90]))

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
