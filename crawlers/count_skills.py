"""
count_skills.py — How many skills do we *really* have?

The headline "N skills" counts SKILL.md FILES. But the corpus is full of copies:
mega-collections re-publish each other, and the same skill appears verbatim (or
near-verbatim) in many repos. This script reports a deduplication funnel so the
honest unique count is explicit and reproducible.

Funnel (each row collapses more):
  1. raw crawl records            every (repo, file_path) row across all crawls
  2. Claude SKILL.md with content the files we actually fetched
     (+ Gemini files catalogued by metadata only — listed, not counted as built)
  3. distinct (repo, file_path)   de-duplicated by location (the loader already does this)
  4. distinct exact bodies        byte-identical copies collapsed (intra- + cross-repo)
  5. distinct skills (near-dup)    ← BEST "real" count: exact + ≥0.80 Jaccard near-copies
                                     collapsed via union-find (same method as lineage_trace)
  6. distinct concepts            most aggressive: same idea regardless of wording

Writes data/unique_counts.json and prints the funnel.

Usage:  python crawlers/count_skills.py
"""
import json
import sys
import hashlib
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from score_corpus import load_all_crawls
from lineage_trace import norm_body, concept, shingles, jaccard   # reuse the methods

BASE = Path(__file__).parent.parent
OUT = BASE / 'data' / 'unique_counts.json'
NEAR_DUP_THRESHOLD = 0.80   # same as lineage_trace's cross-repo clustering


def _components(items):
    """Union-find over content-bearing skills: union exact-body matches, then
    fuzzy (Jaccard ≥ threshold) within shared concept-name groups. Returns the
    number of connected components = unique skills after near-dup collapse."""
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    # exact body
    by_hash = defaultdict(list)
    for i, it in enumerate(items):
        by_hash[it['h']].append(i)
    for idxs in by_hash.values():
        for j in idxs[1:]:
            union(idxs[0], j)

    # fuzzy within concept groups (bounded; identical to lineage_trace)
    by_concept = defaultdict(list)
    for i, it in enumerate(items):
        if it['concept']:
            by_concept[it['concept']].append(i)
    for idxs in by_concept.values():
        if len(idxs) < 2:
            continue
        sh = {i: shingles(items[i]['body']) for i in idxs}
        for a in range(len(idxs)):
            for b in range(a + 1, len(idxs)):
                i, j = idxs[a], idxs[b]
                if find(i) != find(j) and jaccard(sh[i], sh[j]) >= NEAR_DUP_THRESHOLD:
                    union(i, j)

    return len({find(i) for i in range(len(items))})


def main():
    records = load_all_crawls()
    raw = len(records)

    claude = [r for r in records if r.get('skill_md_content')]
    gemini = [r for r in records
              if r.get('file_format') == 'gemini' and not r.get('skill_md_content')]

    # distinct location is already guaranteed by the loader's (repo, path) merge
    distinct_location = len({(r['repo_full_name'], r['file_path']) for r in claude})

    # build items for dedup
    items = []
    for r in claude:
        body = norm_body(r['skill_md_content'])
        _p = r['file_path'].replace('\\', '/').split('/')
        name = _p[-2] if len(_p) >= 2 else _p[-1]
        items.append({
            'repo': r['repo_full_name'],
            'h': hashlib.sha1(body.encode()).hexdigest(),
            'concept': concept(name),
            'body': body,
        })

    distinct_exact = len({it['h'] for it in items})
    distinct_near = _components(items)
    distinct_concepts = len({it['concept'] for it in items if it['concept']})

    # how much of the corpus is duplication
    copy_share = round(100 * (len(items) - distinct_near) / len(items), 1) if items else 0

    funnel = {
        'raw_crawl_records': raw,
        'claude_with_content': len(claude),
        'gemini_metadata_only': len(gemini),
        'distinct_location': distinct_location,
        'distinct_exact_bodies': distinct_exact,
        'distinct_skills_near_dup': distinct_near,
        'distinct_concepts': distinct_concepts,
        'duplicate_share_pct': copy_share,
        'near_dup_threshold': NEAR_DUP_THRESHOLD,
    }
    OUT.write_text(json.dumps(funnel, indent=1))

    print('How many skills do we really have?\n')
    print(f"  raw crawl records ............... {raw:>6,}")
    print(f"  Claude SKILL.md w/ content ...... {len(claude):>6,}")
    print(f"  (Gemini, metadata only) ........ {len(gemini):>6,}   catalogued, not counted")
    print(f"  distinct (repo, file_path) ..... {distinct_location:>6,}")
    print(f"  distinct exact bodies .......... {distinct_exact:>6,}   exact copies collapsed")
    print(f"  distinct skills (near-dup) ..... {distinct_near:>6,}   ← REAL unique skills")
    print(f"  distinct concepts .............. {distinct_concepts:>6,}   same idea, any wording")
    print(f"\n  ~{copy_share}% of fetched files are exact/near duplicates of another skill.")
    print(f"  wrote {OUT}")


if __name__ == '__main__':
    main()
