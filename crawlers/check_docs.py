"""
check_docs.py — Flag headline numbers in the narrative docs that disagree with
the live corpus (data/corpus_stats.json). It does NOT auto-edit prose (too
fragile); it warns, so drift is caught instead of silently shipped.

Checks the load-bearing figures: skill count, repo count, median quality,
WHEN-trigger %. Ignores numbers inside explicit "Correction"/"Update"/historical
blockquotes (they intentionally cite old values).

Also checks README.md at the repo root — its badges (shields.io
"skills-N"/"repos-N") and intro paragraph are load-bearing headline figures
too, but live outside docs/ where the rest of this script looks. This check
exists because that exact gap let README drift to "4,902 skills across 39
repositories" while docs/STATS.md (generated) already said 4,975 / 43 (see
PR #16).

Usage:  python crawlers/check_docs.py      # exit 1 if any doc is stale
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
STATS = BASE / 'data' / 'corpus_stats.json'
GRAPH = BASE / 'data' / 'graph_data_v2.json'
DOCS = BASE / 'docs'
README = BASE / 'README.md'

# The line in README.md that describes the *interactive graph* dataset (a
# curated subset, deliberately different from n_skills/n_repos above — see
# other_dataset_ctx). Nothing previously re-derived these four numbers from
# the graph data itself, which is exactly the gap that let a spam PR (#1,
# Xquik-dev, 2026-06-24) change them without anything noticing, and let
# index.html's domain counter sit wrong (15 vs the actual 13) independent of
# that incident. This regex is intentionally specific to that one sentence
# rather than a generic scan, since "skills"/"organizations"/"nodes"/"links"
# are common words elsewhere in the doc.
IG_LINE = re.compile(
    r'\*\*Interactive graph\*\*.*?:\s*([\d,]+)\s*skills across\s*([\d,]+)\s*organi[sz]ations.*?'
    r'([\d,]+)\s*nodes,\s*([\d,]+)\s*links,\s*(\d+)\s*domains',
    re.S,
)


def graph_truth():
    """Recompute the interactive-graph headline figures directly from the
    data, rather than trusting whatever prose last hand-typed them."""
    if not GRAPH.exists():
        return None
    g = json.load(open(GRAPH))
    domains = [n for n in g['nodes'] if n.get('type') == 'domain']
    orgs = [n for n in g['nodes'] if n.get('type') == 'org']
    return {
        'skills': sum(n.get('count', 0) for n in domains),
        'orgs': len(orgs),
        'nodes': len(g['nodes']),
        'links': len(g['links']),
        'domains': len(domains),
    }


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
    # README describes two distinct datasets: the full raw-crawl corpus (what
    # n_skills/n_repos track) and the interactive graph's curated subset from
    # VoltAgent/awesome-agent-skills, which is a smaller, intentionally
    # different number. Don't flag the latter as drift against the former.
    other_dataset_ctx = re.compile(r'organi[sz]ations?|VoltAgent|curated index', re.I)

    # GENERIC drift check: flag a stale corpus total WITHOUT hand-enumerating old
    # constants — but ONLY on lines phrased as the headline ("N skills across …",
    # "collected/​swept/​crawled N …"). That cue is what distinguishes the corpus
    # total from the many legitimate per-repo "66 skills" counts in the docs.
    def _num(s):
        return int(s.replace(',', ''))
    headline_cue = re.compile(r'across|collected|crawled|swept|sweep|corpus|in total|total of', re.I)
    skills_fig = re.compile(r'\b(\d[\d,]*)\s+(?:crawled\s+|published\s+|full\s+)?skills?\b', re.I)
    repos_fig = re.compile(r'\b(\d[\d,]*)\s+repos(?:itories)?\b', re.I)

    # shields.io badges encode the comma as %2C and have no surrounding words
    # ("skills-4%2C975"), so they need their own pattern rather than skills_fig/
    # repos_fig above (which look for a number followed by the word "skills").
    badge_skills_fig = re.compile(r'badge/skills-([\d%,C]+)-', re.I)
    badge_repos_fig = re.compile(r'badge/repos-(\d[\d,]*)-', re.I)

    def _badge_num(s):
        return int(s.replace('%2C', '').replace(',', ''))

    files = sorted(DOCS.glob('*.md'))
    if README.exists():
        files.append(README)

    issues = []
    for md in files:
        if md.name in ('STATS.md',):
            continue
        for i, line in enumerate(md.read_text().splitlines(), 1):
            # Checked unconditionally, before the other_dataset_ctx skip below
            # — that skip exists to exempt this exact line's "organizations"/
            # "VoltAgent"/"curated index" wording from the *other* checks, so
            # it would otherwise skip this check too, right when it matters.
            if md.name == 'README.md':
                m = IG_LINE.search(line)
                if m:
                    truth = graph_truth()
                    if truth is None:
                        issues.append((md.name, i, 'graph_data_v2.json missing — cannot verify',
                                       line.strip()[:90]))
                    else:
                        claimed = {
                            'skills': _num(m.group(1)), 'orgs': _num(m.group(2)),
                            'nodes': _num(m.group(3)), 'links': _num(m.group(4)),
                            'domains': _num(m.group(5)),
                        }
                        mismatches = [f'{k} {claimed[k]} (live: {truth[k]})'
                                      for k in claimed if claimed[k] != truth[k]]
                        if mismatches:
                            issues.append((md.name, i,
                                           'interactive-graph line vs data/graph_data_v2.json: '
                                           + ', '.join(mismatches),
                                           line.strip()[:90]))

            if hist_ctx.search(line) or other_dataset_ctx.search(line):
                continue
            for pat, label in stale_patterns:
                if pat.search(line):
                    issues.append((md.name, i, label, line.strip()[:90]))
            # Badge numbers carry no "across"/"collected" cue text, so check them
            # unconditionally rather than gating on headline_cue like the rest.
            for m in badge_skills_fig.finditer(line):
                if _badge_num(m.group(1)) != n_skills:
                    issues.append((md.name, i,
                                   f'badge skill count {m.group(1)} (live: {n_skills:,})',
                                   line.strip()[:90]))
            for m in badge_repos_fig.finditer(line):
                if _badge_num(m.group(1)) != n_repos:
                    issues.append((md.name, i,
                                   f'badge repo count {m.group(1)} (live: {n_repos})',
                                   line.strip()[:90]))
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
