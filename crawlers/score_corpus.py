"""
score_corpus.py — Score the full crawl corpus and roll up per-repo signatures.

Reads the crawl data.json, scores every SKILL.md with skill_quality, classifies
each repo with repo_signature, and writes:

    data/skill_quality.json   per-skill scores + per-repo + per-signature rollups

This is the heuristic pass over all ~5,320 skills (fast, free, repeatable).
The LLM deep-read on a stratified sample is sample_llm.py.

Usage:
    python crawlers/score_corpus.py
"""
import json
import statistics as st
from pathlib import Path
from collections import defaultdict

from skill_quality import score_skill
from repo_signature import classify_repo

BASE = Path(__file__).parent.parent
CRAWLS_DIR = BASE / 'crawls'
OUT = BASE / 'data' / 'skill_quality.json'


def load_all_crawls():
    """Merge results across every crawls/*/data.json. On duplicate
    (repo, file_path), the most recent crawl (by dir name) wins."""
    merged = {}
    for data_path in sorted(CRAWLS_DIR.glob('*/data.json')):
        for r in json.load(open(data_path)).get('results', []):
            merged[(r['repo_full_name'], r['file_path'])] = r
    return list(merged.values())


def main():
    results = load_all_crawls()
    sib_path = BASE / 'data' / 'sibling_files.json'
    siblings = json.load(open(sib_path)) if sib_path.exists() else {}

    per_skill = []
    by_repo = defaultdict(list)
    repo_meta = {}

    for it in results:
        md = it.get('skill_md_content')
        if not md:
            continue
        rn = it['repo_full_name']
        _parts = it['file_path'].replace('\\', '/').split('/')
        dir_name = _parts[-2] if len(_parts) >= 2 else None
        sc = score_skill(md, dir_name,
                         siblings.get(f"{rn}\t{it['file_path']}"))
        rec = {
            'repo': rn,
            'file_path': it['file_path'],
            'name': sc['metrics']['name'] or dir_name,
            'overall': sc['overall'],
            'grade': sc['grade'],
            'scores': sc['scores'],
            'flags': sc['flags'],
            'desc_words': sc['metrics']['desc_words'],
            'body_words': sc['metrics']['body_words'],
            'desc_has_when': sc['metrics']['desc_has_when'],
            'desc_has_anti': sc['metrics']['desc_has_anti_trigger'],
            'ref_files': sc['metrics']['ref_files'],
        }
        per_skill.append(rec)
        by_repo[rn].append(rec)
        if rn not in repo_meta:
            repo_meta[rn] = {
                'stars': it.get('repo_stars'),
                'owner_type': it.get('repo_owner_type'),
                'source': it.get('repo_source'),
                'topics': it.get('repo_topics'),
                'description': it.get('repo_description'),
            }

    # Per-repo rollups + signatures
    repos_out = {}
    for rn, recs in by_repo.items():
        ov = [r['overall'] for r in recs]
        med = st.median(ov)
        std = st.pstdev(ov) if len(ov) > 1 else 0.0
        when_rate = 100 * sum(r['desc_has_when'] for r in recs) / len(recs)
        meta = repo_meta[rn]
        sig = classify_repo({
            'n_skills': len(recs),
            'owner_type': meta['owner_type'],
            'stars': meta['stars'],
            'median_quality': med,
            'quality_stdev': std,
            'pct_with_when': when_rate,
            'source': meta['source'],
        })
        # flag frequency in this repo
        flagct = defaultdict(int)
        for r in recs:
            for f in r['flags']:
                flagct[f] += 1
        repos_out[rn] = {
            'n_skills': len(recs),
            'stars': meta['stars'],
            'owner_type': meta['owner_type'],
            'source': meta['source'],
            'median_quality': round(med, 1),
            'mean_quality': round(st.mean(ov), 1),
            'quality_stdev': round(std, 1),
            'grade_dist': _grade_dist(recs),
            'signature': sig['signature'],
            'signature_rationale': sig['rationale'],
            'pct_with_when': round(100 * sum(r['desc_has_when'] for r in recs) / len(recs), 1),
            'pct_uses_refs': round(100 * sum(r['ref_files'] > 0 for r in recs) / len(recs), 1),
            'top_flags': sorted(flagct.items(), key=lambda x: -x[1])[:5],
        }

    # Per-signature rollups
    by_sig = defaultdict(list)
    for rn, r in repos_out.items():
        by_sig[r['signature']].append(rn)
    sig_out = {}
    for sig, repolist in by_sig.items():
        recs = [r for rn in repolist for r in by_repo[rn]]
        ov = [r['overall'] for r in recs]
        flagct = defaultdict(int)
        for r in recs:
            for f in r['flags']:
                flagct[f] += 1
        sig_out[sig] = {
            'n_repos': len(repolist),
            'n_skills': len(recs),
            'repos': repolist,
            'median_quality': round(st.median(ov), 1),
            'mean_quality': round(st.mean(ov), 1),
            'pct_with_when': round(100 * sum(r['desc_has_when'] for r in recs) / len(recs), 1),
            'pct_uses_refs': round(100 * sum(r['ref_files'] > 0 for r in recs) / len(recs), 1),
            'top_flags': sorted(flagct.items(), key=lambda x: -x[1])[:6],
        }

    # Corpus-wide
    allov = [r['overall'] for r in per_skill]
    allflag = defaultdict(int)
    for r in per_skill:
        for f in r['flags']:
            allflag[f] += 1
    corpus = {
        'n_skills': len(per_skill),
        'n_repos': len(repos_out),
        'median_quality': round(st.median(allov), 1),
        'mean_quality': round(st.mean(allov), 1),
        'grade_dist': _grade_dist(per_skill),
        'pct_with_when': round(100 * sum(r['desc_has_when'] for r in per_skill) / len(per_skill), 1),
        'pct_with_anti_trigger': round(100 * sum(r['desc_has_anti'] for r in per_skill) / len(per_skill), 1),
        'pct_uses_refs': round(100 * sum(r['ref_files'] > 0 for r in per_skill) / len(per_skill), 1),
        'flag_freq': sorted(allflag.items(), key=lambda x: -x[1]),
    }

    out = {'corpus': corpus, 'signatures': sig_out,
           'repos': repos_out, 'skills': per_skill}
    OUT.write_text(json.dumps(out, indent=1))
    print(f'wrote {OUT}  ({len(per_skill)} skills, {len(repos_out)} repos)')
    print(f"corpus median quality: {corpus['median_quality']}  "
          f"grade dist: {corpus['grade_dist']}")
    print(f"  pct with WHEN-trigger: {corpus['pct_with_when']}%  "
          f"pct uses refs: {corpus['pct_uses_refs']}%")
    for sig, s in sorted(sig_out.items(), key=lambda x: -x[1]['median_quality']):
        print(f"  {sig:20s} repos={s['n_repos']:2d} skills={s['n_skills']:5d} "
              f"median={s['median_quality']:.1f} when={s['pct_with_when']:.0f}%")


def _grade_dist(recs):
    d = defaultdict(int)
    for r in recs:
        d[r['grade']] += 1
    return dict(sorted(d.items()))


if __name__ == '__main__':
    main()
