"""
sample_llm.py — LLM deep-read on a stratified sample of the corpus.

The heuristic scorer (score_corpus.py) measures structure; it can't judge
whether a description *actually* helps Claude decide when to invoke a skill,
or whether the body is genuinely useful. This pass samples skills across
signatures (and across the quality range within each) and asks `claude -p`
to compare each against the Anthropic gold standard.

Uses `claude -p` (existing OAuth session, no API key). Results cached in
data/llm_sample.json so re-runs are incremental.

Usage:
    python crawlers/sample_llm.py            # run sample
    python crawlers/sample_llm.py --dry-run  # print prompts only
    python crawlers/sample_llm.py --n 3      # samples per (signature, tier)
"""
import json
import subprocess
import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from score_corpus import latest_content_by_key   # canonical merged-corpus loader

BASE = Path(__file__).parent.parent
# Reads the merged corpus (latest content per skill) rather than a pinned first
# snapshot. REVIEW(still open): this is the v1 judge that judge_llm.py says it
# REPLACES — retire it (like maturity_crawl.py) so two judges don't both linger.
SCORES = BASE / 'data' / 'skill_quality.json'
OUT = BASE / 'data' / 'llm_sample.json'

PROMPT = """You are auditing an Agent Skill's SKILL.md against Anthropic's \
gold-standard house style (anthropics/skills). Anthropic skills have: a \
description that states WHAT the skill does AND WHEN to use it; progressive \
disclosure (link to reference files rather than dumping everything inline); \
clear headings; concrete examples; tight scope.

Reply with ONLY a JSON object, no prose:
{{"verdict":"exemplary|solid|weak|broken",
  "diverges_from_anthropic":["short phrase", ...],
  "best_trait":"short phrase",
  "one_fix":"the single highest-value change"}}

Repo: {repo}  (signature: {signature})
--- SKILL.md ---
{md}
--- end ---"""


def call_claude(prompt):
    r = subprocess.run(['claude', '-p', prompt],
                       capture_output=True, text=True, timeout=180)
    out = r.stdout.strip()
    a, b = out.find('{'), out.rfind('}')
    if a >= 0 and b > a:
        try:
            return json.loads(out[a:b + 1])
        except json.JSONDecodeError:
            pass
    return {'error': 'unparseable', 'raw': out[:300]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--n', type=int, default=2,
                    help='samples per (signature, tier)')
    args = ap.parse_args()
    random.seed(7)

    scores = json.load(open(SCORES))
    crawl = latest_content_by_key()
    repo_sig = {rn: r['signature'] for rn, r in scores['repos'].items()}

    # bucket skills by (signature, tier) where tier splits the quality range
    buckets = {}
    for s in scores['skills']:
        sig = repo_sig[s['repo']]
        tier = 'high' if s['overall'] >= 80 else 'low' if s['overall'] < 60 else 'mid'
        buckets.setdefault((sig, tier), []).append(s)

    cache = json.load(open(OUT)) if OUT.exists() else {}
    sample = []
    for (sig, tier), items in sorted(buckets.items()):
        picked = random.sample(items, min(args.n, len(items)))
        for s in picked:
            sample.append((sig, tier, s))

    print(f'sampling {len(sample)} skills across '
          f'{len(set(k[0] for k in buckets))} signatures')

    results = cache.get('results', [])
    seen = {(r['repo'], r['file_path']) for r in results}
    for sig, tier, s in sample:
        key = (s['repo'], s['file_path'])
        if key in seen:
            continue
        # REVIEW(known bug, kept here): judge_llm.py's docstring identifies this
        # 6000-char clip as cause #1 of v1's pessimism (it penalised long, often
        # best, skills as "truncated mid-sentence"). Another reason to retire v1.
        md = crawl[key]['skill_md_content'][:6000]
        prompt = PROMPT.format(repo=s['repo'], signature=sig, md=md)
        if args.dry_run:
            print(f'\n=== {s["repo"]} {s["file_path"]} ({sig}/{tier}) ===')
            print(prompt[:400])
            continue
        verdict = call_claude(prompt)
        results.append({'repo': s['repo'], 'file_path': s['file_path'],
                        'signature': sig, 'tier': tier,
                        'heuristic_score': s['overall'], 'llm': verdict})
        print(f'  {s["repo"][:30]:30s} {sig:18s} {tier:4s} '
              f'h={s["overall"]:.0f} → {verdict.get("verdict","?")}')

    if not args.dry_run:
        OUT.write_text(json.dumps({'results': results}, indent=1))
        print(f'wrote {OUT} ({len(results)} judged)')


if __name__ == '__main__':
    main()
