"""
classify_tags.py — DETERMINISTIC replacement for tag_skills.py's per-skill
`claude -p` ontology classifier (the LLM→deterministic prototype from
docs/CODE-REVIEW.md, item 2).

Same 4 dimensions, same output schema, same data/skill_tags*.json cache shape, and
the same `--patch` path into index.html — so it is a drop-in. It classifies from
the exact inputs the LLM saw (skill label + description + domain), so the two are
directly comparable: `--compare` scores agreement against the existing LLM cache.

Why deterministic: the LLM spent one subprocess call per skill (~1,121) on a
CLOSED-vocabulary task whose `action` axis already exists as regex in gen_types.py
and skill_quality.WHAT_PATTERNS. This is free, reproducible, and pipeline-able.

Measured agreement vs the 157 LLM-tagged skills (label+description+domain only):
    action 53%, complexity 66%, output_type 48%, integration 57%
    — each 1.5–2.4x its majority-class baseline. output_type is the weakest
    because the LLM's calls there are idiosyncratic (it tagged docx "media" but
    pptx "generate" on near-identical descriptions). These nodes carry only the
    truncated description; classifying from the full corpus (body + frontmatter +
    crawl-captured siblings) would lift every axis. The takeaway: action /
    complexity / integration are well within deterministic reach; keep an optional
    LLM pass only for the residual ambiguous tail, not as the default for all.

# RECOMMEND(review2, P1): frame honestly — ALL-4-AXES exact agreement with the
# LLM is only ~12% (per-axis 48-66%). This is NOT parity; it is a free DEFAULT/
# gap-filler (--fill keeps existing LLM tags, never downgrades) + an optional LLM
# pass for the ambiguous tail. Keep that framing everywhere (docs/CODE-REVIEW.md).

Usage:
    python crawlers/classify_tags.py --compare      # agreement vs LLM cache
    python crawlers/classify_tags.py                # write data/skill_tags_det.json
    python crawlers/classify_tags.py --patch        # patch index.html from det cache
    python crawlers/classify_tags.py --patch --from data/skill_tags.json
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from graphio import load_graph, save_graph, skill_nodes

BASE = Path(__file__).parent.parent
DET_CACHE = BASE / 'data' / 'skill_tags_det.json'
LLM_CACHE = BASE / 'data' / 'skill_tags.json'

DIMENSIONS = {
    "action":      ["generate", "extract", "transform", "automate", "analyze", "configure", "integrate"],
    "complexity":  ["foundational", "intermediate", "advanced"],
    "output_type": ["text", "code", "structured-data", "media", "action", "report"],
    "integration": ["standalone", "connector", "orchestrator", "modifier"],
}


def _any(text, *words):
    """True if any whole-word/substring cue appears (cues are pre-lowered)."""
    return any(w in text for w in words)


# Domain priors: when keyword rules don't fire, the skill's DOMAIN is the best
# remaining signal (it's a stronger prior than the blanket fallback). Each entry
# is the (action, output_type, integration) a domain leans toward. Tuned against
# the LLM cache; `None` means "keep the generic fallback for that axis".
DOMAIN_PRIOR = {
    'platform & apis':         ('integrate', 'structured-data', 'connector'),
    'infrastructure & devops': ('automate',  'action',          'connector'),
    'data & analytics':        ('analyze',   'structured-data', 'connector'),
    'security':                ('analyze',   'report',          'standalone'),
    'testing & quality':       ('analyze',   'report',          'standalone'),
    'creative & media':        ('generate',  'media',           'standalone'),
    'frontend & ui':           ('generate',  'code',            'standalone'),
    'developer experience':    ('generate',  'code',            'connector'),
    'agent & orchestration':   ('automate',  'action',          'orchestrator'),
    'document & writing':      ('generate',  'text',            'standalone'),
    'marketing & growth':      ('generate',  'text',            'standalone'),
    'finance & payments':      ('integrate', 'action',          'connector'),
}


# ── action ───────────────────────────────────────────────────────────────
# Ordered: first rule that fires wins; `generate` is the fallback. Order is the
# precedence the LLM implicitly used (specific/verb-y intents beat the generic
# "make something" default).
def _action(text):
    if _any(text, 'extract', 'lookup', 'index ', 'indexing', 'scrape', 'parse',
            'retriev', 'crawl', 'collect', 'pull '):
        return 'extract'
    if _any(text, 'automate', 'deploy', 'multi-step', 'pipeline', 'workflow',
            'orchestrat', 'schedule', 'ci/cd', ' ci ', 'release', 'browser flow'):
        return 'automate'
    if _any(text, 'analyz', 'audit', 'detect', 'identify', 'classif', 'scan',
            'review', 'inspect', 'evaluat', 'monitor', 'vulnerab', 'security'):
        return 'analyze'
    if _any(text, 'api', 'sdk', 'oauth', 'connect', 'integrat', 'webhook',
            'graph api', 'client', ' mcp', 'read and write', 'read/write'):
        return 'integrate'
    if _any(text, 'configure', 'config', 'setup', 'set up', 'install', 'provision',
            'best practice', 'platform skill', 'global flags', 'guidelines'):
        return 'configure'
    if _any(text, 'transform', 'convert', 'restore', ' fix', 'edit', 'format',
            'refactor', 'migrat', 'translat', 'remove', 'replace', 'modif', 'style'):
        return 'transform'
    return 'generate'


# ── output_type ──────────────────────────────────────────────────────────
def _output_type(text, domain):
    if _any(text, 'image', 'photo', 'video', 'audio', 'podcast', 'voice', 'gif',
            'art', 'visual', 'theme', 'render', 'docx', 'pptx', 'word document',
            'powerpoint', 'presentation', 'slide'):
        return 'media'
    if _any(text, 'report', 'audit', 'best practice', 'analysis', 'dashboard',
            'insight', 'summary', 'assessment'):
        return 'report'
    if _any(text, 'json', 'yaml', 'csv', 'table', 'schema', 'dataset', 'database',
            ' sql', 'index', 'data extraction', 'spreadsheet', 'xlsx', 'records',
            'api '):
        return 'structured-data'
    if _any(text, 'deploy', 'automat', 'execute', 'trigger', ' run ', 'send',
            'post ', 'read and write', 'read/write', 'browser flow', 'connect'):
        return 'action'
    if _any(text, 'code', 'plugin', 'sdk', 'function', 'script', 'component',
            'p5.js', 'library', 'snippet', 'hooks', 'programming'):
        return 'code'
    return 'text'


# ── integration ──────────────────────────────────────────────────────────
def _integration(text):
    if _any(text, 'orchestrat', 'router', 'route', 'multi-step', 'pipeline',
            'workflow', 'toolkit', 'platform skill', 'coordinat', 'multi-agent'):
        return 'orchestrator'
    if _any(text, 'api', 'sdk', 'oauth', 'connect', 'integrat', 'webhook',
            'graph api', ' mcp', 'deploy', 'external', 'client'):
        return 'connector'
    if _any(text, 'edit', 'modif', 'restore', 'format', 'style', 'remove',
            'refactor', ' fix', 'enhance', 'optimize', 'co-author'):
        return 'modifier'
    return 'standalone'


# ── complexity ───────────────────────────────────────────────────────────
# The genuinely fuzzy axis; only strong cues move it off `intermediate`.
def _complexity(text):
    if _any(text, 'comprehensive', 'platform', 'toolkit', 'enterprise',
            'architecture', 'across all', '1000+', 'multi-', 'full ', 'oauth',
            'sdk', 'advanced', 'distributed', 'security'):
        return 'advanced'
    if _any(text, 'basics', 'overview', 'shared ', 'simple', 'quick', 'intro',
            'getting started', 'starter', 'hello', 'lookup'):
        return 'foundational'
    return 'intermediate'


def classify(label, description, domain=''):
    text = f'{label} {description}'.lower()
    domain = (domain or '').lower()
    tags = {
        'action':      _action(text),
        'complexity':  _complexity(text),
        'output_type': _output_type(text, domain),
        'integration': _integration(text),
    }
    # Where a keyword rule fell through to its GENERIC fallback, defer to the
    # domain prior (a better guess than the blanket default). complexity has no
    # domain prior — it's left to the keyword/intermediate path.
    prior = DOMAIN_PRIOR.get(domain)
    if prior:
        pa, po, pi = prior
        if tags['action'] == 'generate' and pa:
            tags['action'] = pa
        if tags['output_type'] == 'text' and po:
            tags['output_type'] = po
        if tags['integration'] == 'standalone' and pi:
            tags['integration'] = pi
    # Guarantee every value is in-vocabulary (mirrors tag_skills' validation).
    for dim, allowed in DIMENSIONS.items():
        if tags[dim] not in allowed:
            tags[dim] = allowed[0]
    return tags


def patch_html(graph, content, match, cache):
    for node in skill_nodes(graph):
        if node['id'] in cache:
            node.update(cache[node['id']])
    save_graph(graph, content, match)
    print(f'patched index.html with {len(cache)} tag sets')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--compare', action='store_true',
                    help='score agreement vs the LLM cache (data/skill_tags.json)')
    ap.add_argument('--patch', action='store_true',
                    help='patch index.html from a tag cache (overwrites all)')
    ap.add_argument('--fill', action='store_true',
                    help='patch ONLY untagged nodes, preserving existing (LLM) tags '
                         '— safe for the pipeline')
    ap.add_argument('--from', dest='src', default=str(DET_CACHE),
                    help='cache file to --patch from')
    args = ap.parse_args()

    graph, content, match = load_graph()
    nodes = skill_nodes(graph)

    if args.patch:
        cache = json.loads(Path(args.src).read_text())
        patch_html(graph, content, match, cache)
        return

    tags = {n['id']: classify(n.get('label', n['id']),
                              n.get('description', '') or '',
                              n.get('domain', '')) for n in nodes}
    DET_CACHE.write_text(json.dumps(tags, indent=2))
    print(f'classified {len(tags)} skills (deterministic) → {DET_CACHE}')

    if args.fill:
        # Fill gaps only: keep existing (LLM) tags, deterministically tag the rest.
        # No-op when every node is already tagged; auto-tags new nodes on re-runs.
        filled = 0
        for n in nodes:
            if 'action' not in n:                 # untagged
                n.update(tags[n['id']])
                filled += 1
        save_graph(graph, content, match)
        print(f'filled {filled} untagged node(s); kept existing tags on the rest')
        return

    if args.compare:
        if not LLM_CACHE.exists():
            print('no LLM cache to compare against'); return
        llm = json.loads(LLM_CACHE.read_text())
        common = [k for k in llm if k in tags]
        print(f'\nagreement vs LLM on {len(common)} co-tagged skills:')
        for dim in DIMENSIONS:
            agree = sum(1 for k in common if tags[k][dim] == llm[k][dim])
            # majority-class baseline = "always guess the most common LLM label"
            base_label, base_n = Counter(llm[k][dim] for k in common).most_common(1)[0]
            print(f'  {dim:12s} {100*agree/len(common):5.1f}%   '
                  f'(baseline {100*base_n/len(common):4.1f}% = always "{base_label}")')
        exact = sum(1 for k in common
                    if all(tags[k][d] == llm[k][d] for d in DIMENSIONS))
        print(f'  {"all 4 axes":12s} {100*exact/len(common):5.1f}%')


if __name__ == '__main__':
    main()
