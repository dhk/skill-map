"""
repo_signature.py — Classify a skills repository by its "signature".

A signature is a coarse repo archetype computed from *observable* features
(skill count, ownership, quality median + variance) so it generalises to
private repos that carry no pre-existing labels. The signature drives the
"if your repo looks like X, do Y" playbook in docs/repo-signature-playbook.md.

Signatures (by scale, then refined by consistency / ownership):

  canonical-reference  official-org, small & curated, high + consistent quality
  mega-collection      >= 250 skills (aggregated dumps, high variance typical)
  marketplace          60–249 skills (multi-domain marketplaces / catalogs)
  domain-pack          15–59 skills, usually one subject area
  boutique             5–14 skills, personal/curated
  single-skill         < 5 skills (one tool, often embedded in a product repo)

Public API:
    classify_repo(stats) -> dict(signature, rationale, confidence)

where `stats` is a dict with (missing keys tolerated):
    n_skills, owner_type ('Organization'|'User'), stars,
    median_quality, quality_stdev, source (optional crawl hint)
"""


def _bucket_by_scale(n):
    if n < 5:    return 'single-skill'
    if n < 15:   return 'boutique'
    if n < 60:   return 'domain-pack'
    if n < 250:  return 'marketplace'
    return 'mega-collection'


def classify_repo(stats):
    n = stats.get('n_skills', 0) or 0
    owner = stats.get('owner_type') or ''
    med = stats.get('median_quality')
    std = stats.get('quality_stdev')
    source = stats.get('source') or ''
    when = stats.get('pct_with_when')

    sig = _bucket_by_scale(n)
    rationale = [f'{n} skills → {sig} by scale']
    confidence = 0.7

    # Promotion to canonical-reference: official org, curated size, high &
    # consistent quality — AND strong triggering discipline. The defining trait
    # of the gold standard is that its skills say WHEN to use them; a tidy,
    # org-owned repo with poor triggers (e.g. a popular single design skill) is
    # NOT canonical just because its heuristic scores are tight.
    is_official = (owner == 'Organization') or source == 'canonical'
    if (sig in ('domain-pack', 'boutique')
            and is_official
            and med is not None and med >= 80
            and (std is None or std <= 18)
            and (when is None or when >= 70)):
        sig = 'canonical-reference'
        rationale.append(
            f'official org + high consistent quality '
            f'(median {med:.0f}, stdev {std if std is None else round(std,1)}, '
            f'WHEN {when if when is None else round(when)}%) '
            f'→ promoted to canonical-reference')
        confidence = 0.85

    # Embedded-in-product hint: a single skill living in a big non-skills repo.
    if sig == 'single-skill' and source == 'embedded':
        rationale.append('skill embedded in a product/docs repo')

    # Quality-variance colouring (informational, doesn't change bucket).
    if std is not None and std > 22 and n >= 15:
        rationale.append(
            f'high quality variance (stdev {std:.1f}) — inconsistent house style')

    return {'signature': sig, 'rationale': '; '.join(rationale),
            'confidence': confidence}


# Per-signature playbook hooks consumed by audit_repo.py / the docs study.
SIGNATURE_GUIDANCE = {
    'canonical-reference': {
        'summary': 'Small, curated, high-consistency. The bar everyone else is measured against.',
        'do': [
            'Keep the set tight — every skill earns its place.',
            'Maintain a SKILL.md template and lint new skills against it.',
            'Use progressive disclosure: link to reference files for depth.',
        ],
    },
    'mega-collection': {
        'summary': 'Huge aggregation. Quality variance is your biggest risk, not coverage.',
        'do': [
            'Run a quality gate in CI — reject skills below grade C.',
            'Deduplicate: large collections accrete near-identical skills.',
            'Add WHEN-triggers to descriptions so retrieval can disambiguate.',
        ],
    },
    'marketplace': {
        'summary': 'Multi-domain catalog. Consistency across contributors is the challenge.',
        'do': [
            'Adopt a shared frontmatter schema and validate on PR.',
            'Group by domain and keep naming conventions uniform.',
            'Trim stub skills (<40-word bodies) — they dilute the catalog.',
        ],
    },
    'domain-pack': {
        'summary': 'Focused on one subject area. Depth matters more than breadth.',
        'do': [
            'Make descriptions trigger precisely within the domain.',
            'Cross-link related skills; add reference material for depth.',
            'Match name to directory and keep slugs consistent.',
        ],
    },
    'boutique': {
        'summary': 'Small personal set. Easy to bring fully up to the gold standard.',
        'do': [
            'Audit each skill against the rubric — at this size, aim for all-A.',
            'Add the WHEN-trigger pattern to every description.',
            'Add headings + a concrete example to thin bodies.',
        ],
    },
    'single-skill': {
        'summary': 'One skill, often embedded in a larger product. Make it exemplary.',
        'do': [
            'Treat the single SKILL.md as a showcase — full frontmatter, clear trigger.',
            'If it is growing, split into multiple skills before it becomes a dump.',
        ],
    },
}


if __name__ == '__main__':
    import json
    import sys
    stats = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    print(json.dumps(classify_repo(stats), indent=2))
