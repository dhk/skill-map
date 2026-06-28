"""
skill_quality.py — Score any SKILL.md against the Anthropic gold-standard rubric.

The rubric is derived empirically from the canonical reference skills
(anthropics/skills, openai/skills). See docs/best-practices.md for the
narrative; the thresholds encoded here are the machine-readable version.

Four weighted dimensions (each 0–100), combined into an overall score:

  frontmatter   (25%)  name/description present, valid slug, valid YAML,
                       license/metadata, no junk keys
  triggering    (30%)  description says WHAT + WHEN (the "Use this when…"
                       pattern Anthropic models), healthy length
  disclosure    (20%)  progressive disclosure — body present, token economy,
                       links to reference files instead of dumping everything
  structure     (25%)  headings, examples/code where appropriate, steps/bullets,
                       not a stub

Public API:
    parse_skill(md)        -> dict(frontmatter, body, raw)
    score_skill(md, name)  -> dict(scores, overall, grade, flags, metrics)

Usable standalone (`python crawlers/skill_quality.py path/to/SKILL.md`) and
imported by audit_repo.py / score_corpus.py.
"""
import re
import sys
import json

# ── Thresholds (derived from canonical reference skills) ──────────────
# REVIEW(assumption / fragile): every threshold below is a magic constant frozen
# from one snapshot of anthropics/skills (desc median 43 words, body ~1194, etc.).
# They are NOT recomputed from the live corpus, so as the canonical reference
# evolves these silently drift from "what the gold standard actually does now".
# Since score_corpus already loads the full corpus, the canonical percentiles
# could be derived at runtime and these constants become a fallback, not the law.
#
# REVIEW(LLM-replaceable, the GOOD direction): this whole module is the
# deterministic counterpart to sample_llm.py / judge_llm.py. Of the LLM judge's
# axes, frontmatter / triggering / disclosure / structure are ALREADY computed
# here for free over the entire corpus; the LLM is only genuinely additive on the
# three judgment axes it flags itself (scope, instruction quality, safety
# appropriateness). The remaining LLM passes should be scoped to just those.
# anthropics/skills: desc median 43 words, body median ~1194 words,
# name+description always present, license common, headings standard.
DESC_MIN_WORDS = 8       # below this a description can't say what+when
DESC_LOW_WORDS = 14      # canonical descriptions rarely shorter
DESC_HIGH_WORDS = 80     # above this it's bloated for a trigger string
BODY_STUB_WORDS = 40     # below this the body is a stub, not a skill
BODY_LONG_WORDS = 2200   # above this without reference files = poor disclosure

# Phrases that signal a "when to use" trigger in the description.
WHEN_PATTERNS = [
    r'\buse (this|it|when|for)\b',
    r'\bwhen (you|the user|users|a user|asked|working|building|creating|dealing)\b',
    r'\bfor (creating|building|generating|analyzing|writing|working|when)\b',
    r'\bif (you|the user|asked)\b',
    r'\btrigger',
    r'\bapply (this|when)\b',
    r'\binvoke',
]
# Phrases that signal an anti-trigger ("when NOT to use"). Surfaced by the
# tuned LLM judge as a real gap even canonical skills miss; a complete
# description states what, when, AND when not (prevents false-positive retrieval).
ANTI_TRIGGER_PATTERNS = [
    r'\b(do not|don\'t|not|never|avoid)\s+(use|apply|invoke|trigger)',
    r'\bnot (for|intended|meant|suitable|appropriate|when)\b',
    r'\b(rather than|instead of|as opposed to)\b',
    r'\b(except|unless|excluding)\b',
    r'\bnot\b.{0,40}\b(standalone|google sheets|word docs?|simple|read-only)\b',
]
# Signals that the skill states its OUTPUT format explicitly (a checklist item:
# "the desired output format is explicit").
OUTPUT_FORMAT_PATTERNS = [
    r'^#{1,4}\s*output', r'\boutput\s*(format|schema|structure)\b',
    r'\b(returns?|produces?|generates?|emits?)\b.{0,40}\b(json|yaml|markdown|table|csv|file|report|format)\b',
    r'\bformat\b.{0,20}:\s*\n',
]
# High-stakes signals: genuinely risky/irreversible operations whose failure is
# costly. Kept tight on purpose — broad terms like "deploy"/"token"/"migrate"
# over-fire, so we require destructive verbs, financial movement, secret
# exposure, or production-deploy specifically.
HIGH_STAKES_PATTERNS = [
    r'\brm\s+-rf\b', r'\b(force[- ]?push|git\s+push\s+--force)\b',
    r'\b(delete|drop|destroy|truncate|wipe|purge)\b.{0,30}'
    r'\b(database|table|production|prod|bucket|volume|repo|branch|record|user)\b',
    r'\b(deploy|release|rollout|ship)\b.{0,30}\b(production|prod\b|live)\b',
    r'\b(payment|charge|refund|invoice|wire\s+transfer|payout|billing)\b',
    r'\b(secret|credential|api[- ]?key|private\s+key|password)\b.{0,30}'
    r'\b(rotat|expos|leak|commit|store|delete|revoke)\w*',
    r'\b(irreversible|cannot be undone|permanently delete|data loss)\b',
]
SAFETY_PATTERNS = [
    r'\b(validat|verif|confirm|dry[- ]?run|rollback|backup|review before|'
    r'check before|idempotent|test first|sanity check|guard)\w*',
    r'\ballowed-tools\b', r'\bdisable-model-invocation\b',
]
# Verbs that signal the description says WHAT the skill does.
WHAT_PATTERNS = [
    r'\b(creat|generat|build|analyz|extract|transform|convert|writ|review|'
    r'test|deploy|configur|manag|automat|format|pars|validat|search|'
    r'design|render|process|summar|translat|debug|refactor|audit|'
    r'integrat|orchestrat|edit|read|fetch|scrap|classif|optimiz)\w*\b',
]

VALID_SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
# Keys the canonical corpus actually uses; anything else is "junk".
KNOWN_KEYS = {
    'name', 'description', 'license', 'metadata', 'allowed-tools',
    'allowed_tools', 'version', 'author', 'tags', 'model', 'argument-hint',
    'disable-model-invocation', 'title',
}


try:
    import yaml as _yaml
except ImportError:           # PyYAML optional: fall back to the hand parser
    _yaml = None


def _fm_manual(fm_text):
    """Fallback frontmatter parser: flat `key: value` + block scalars (|, >)."""
    fm = {}
    lines = fm_text.splitlines()
    i = 0
    while i < len(lines):
        mm = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', lines[i])
        if not mm:
            i += 1
            continue
        key, val = mm.group(1).strip(), mm.group(2).strip()
        if re.match(r'^[|>][-+0-9]*$', val):          # block scalar
            block = []
            i += 1
            while i < len(lines) and (lines[i].strip() == '' or
                                      re.match(r'^\s+', lines[i])):
                block.append(lines[i].strip())
                i += 1
            fm[key] = ' '.join(b for b in block if b).strip()
            continue
        fm[key] = val.strip('"\'')
        i += 1
    return fm


def _coerce_fm(d):
    """Normalise a parsed YAML mapping for scoring: scalars → str, keep
    list/dict (e.g. a nested `metadata:` block) as-is so presence is detectable."""
    out = {}
    for k, v in d.items():
        out[str(k)] = v if isinstance(v, (dict, list)) else ('' if v is None else str(v))
    return out


def parse_skill(md):
    """Split a SKILL.md into frontmatter (dict) and body (str).

    Uses PyYAML when available (handles nested maps, flow lists, quoted/colon
    values correctly) and falls back to a small hand parser when PyYAML is absent
    or the frontmatter is malformed — so scoring never crashes on a bad header.
    """
    md = md or ''
    fm = {}
    body = md
    if md.lstrip().startswith('---'):
        m = re.match(r'^\s*---\s*\n(.*?)\n---\s*\n?(.*)$', md, re.S)
        if m:
            body = m.group(2)
            fm_text = m.group(1)
            if _yaml is not None:
                try:
                    loaded = _yaml.safe_load(fm_text)
                    fm = _coerce_fm(loaded) if isinstance(loaded, dict) else {}
                except _yaml.YAMLError:
                    fm = _fm_manual(fm_text)      # malformed → best-effort
            else:
                fm = _fm_manual(fm_text)
    return {'frontmatter': fm, 'body': body, 'raw': md,
            'has_yaml': bool(fm) or md.lstrip().startswith('---')}


def _count(body, pattern, flags=re.M):
    return len(re.findall(pattern, body, flags))


REF_SIBLING_RE = re.compile(r'(^|/)(reference|references|scripts|assets|docs)/', re.I)


def _metrics(parsed, dir_name=None, sibling_files=None):
    fm = parsed['frontmatter']
    body = parsed['body']
    desc = fm.get('description', '')
    words = body.split()
    ref_files = _count(
        body, r'\]\(([^)]+\.(?:md|py|sh|js|ts|txt|json|ya?ml|csv))\)')
    ref_files += _count(body, r'(?:see|read|refer to|reference)\s+[`\'"]?'
                              r'[\w./-]+\.(?:md|py|sh|txt)', re.I)
    # Real folder contents (backfilled by fetch_siblings.py): does the skill
    # delegate depth to reference/scripts/ sibling files? This is what the
    # progressive-disclosure axis should measure — not just inline links.
    sibs = sibling_files or []
    has_ref_siblings = any(REF_SIBLING_RE.search(p) for p in sibs)
    n_siblings = len(sibs)
    return {
        'has_name': bool(fm.get('name')),
        'has_description': bool(desc),
        'name': fm.get('name', ''),
        'name_valid_slug': bool(VALID_SLUG.match(fm.get('name', ''))),
        'name_matches_dir': (dir_name is None or
                             fm.get('name', '') == dir_name),
        'has_yaml': parsed['has_yaml'],
        'has_license': 'license' in fm,
        'has_metadata': 'metadata' in fm,
        'has_allowed_tools': any(k in fm for k in
                                 ('allowed-tools', 'allowed_tools')),
        'junk_keys': [k for k in fm if k not in KNOWN_KEYS],
        'desc_words': len(desc.split()),
        'desc_has_when': any(re.search(p, desc, re.I) for p in WHEN_PATTERNS),
        'desc_has_what': any(re.search(p, desc, re.I) for p in WHAT_PATTERNS),
        'desc_has_anti_trigger': any(re.search(p, desc, re.I)
                                     for p in ANTI_TRIGGER_PATTERNS),
        'body_words': len(words),
        'h2': _count(body, r'^## '),
        'h3': _count(body, r'^### '),
        'code_blocks': _count(body, r'```') // 2,
        'bullets': _count(body, r'^\s*[-*] '),
        'numbered_steps': _count(body, r'^\s*\d+\. '),
        'ref_files': ref_files,
        'has_ref_siblings': has_ref_siblings,
        'n_siblings': n_siblings,
        'has_output_format': any(re.search(p, body, re.I | re.M)
                                 for p in OUTPUT_FORMAT_PATTERNS),
        'is_high_stakes': any(re.search(p, body, re.I) for p in HIGH_STAKES_PATTERNS),
        'has_safety_posture': any(re.search(p, body, re.I) for p in SAFETY_PATTERNS),
    }


def _score_frontmatter(m):
    s = 0
    if m['has_name']:           s += 30
    if m['has_description']:    s += 30
    if m['has_yaml']:           s += 10
    if m['name_valid_slug']:    s += 12
    if m['name_matches_dir']:   s += 8
    if m['has_license'] or m['has_metadata']: s += 10
    if not m['junk_keys']:      s += 0   # neutral; junk only penalizes below
    s -= min(10, 5 * len(m['junk_keys']))
    return max(0, min(100, s))


def _score_triggering(m):
    if not m['has_description']:
        return 0
    s = 0
    w = m['desc_words']
    if w >= DESC_LOW_WORDS:       s += 25
    elif w >= DESC_MIN_WORDS:     s += 15
    else:                         s += 4
    if w > DESC_HIGH_WORDS:       s -= 10          # bloated trigger string
    if m['desc_has_what']:        s += 25
    if m['desc_has_when']:        s += 35          # the highest-value signal
    if m['desc_has_anti_trigger']: s += 15         # when NOT to use (the rare polish)
    return max(0, min(100, s))


def _score_disclosure(m):
    bw = m['body_words']
    if bw < BODY_STUB_WORDS:
        return 15 if bw > 0 else 0                 # stub
    s = 60                                          # has a real body
    # depth delegated either via inline links OR real reference/scripts siblings
    delegates = m['ref_files'] >= 1 or m['has_ref_siblings']
    if delegates:                 s += 25
    if m['ref_files'] >= 3 or m['n_siblings'] >= 5:  s += 15
    if bw > BODY_LONG_WORDS and not delegates:
        s -= 25                                     # dumps everything inline
    return max(0, min(100, s))


def _score_structure(m):
    if m['body_words'] < BODY_STUB_WORDS:
        return 10
    s = 0
    if m['h2'] + m['h3'] >= 1:    s += 25
    if m['h2'] + m['h3'] >= 3:    s += 15
    if m['code_blocks'] >= 1:     s += 20
    if m['bullets'] + m['numbered_steps'] >= 3: s += 20
    if m['numbered_steps'] >= 1:  s += 10          # procedural guidance
    if m['body_words'] >= 120:    s += 10
    return max(0, min(100, s))


WEIGHTS = {'frontmatter': .25, 'triggering': .30,
           'disclosure': .20, 'structure': .25}


def _grade(overall):
    if overall >= 85: return 'A'
    if overall >= 70: return 'B'
    if overall >= 55: return 'C'
    if overall >= 40: return 'D'
    return 'F'


def score_skill(md, dir_name=None, sibling_files=None):
    """Score a raw SKILL.md string. dir_name enables name==dir checking;
    sibling_files (the skill folder's other files) lets the disclosure axis
    credit reference/scripts delegation instead of inferring it from links."""
    parsed = parse_skill(md)
    m = _metrics(parsed, dir_name, sibling_files)
    scores = {
        'frontmatter': _score_frontmatter(m),
        'triggering':  _score_triggering(m),
        'disclosure':  _score_disclosure(m),
        'structure':   _score_structure(m),
    }
    overall = round(sum(scores[k] * WEIGHTS[k] for k in scores), 1)
    flags = []
    if not m['has_name']:        flags.append('missing-name')
    if not m['has_description']: flags.append('missing-description')
    if not m['name_valid_slug'] and m['has_name']:
        flags.append('non-slug-name')
    if m['has_description'] and not m['desc_has_when']:
        flags.append('no-when-trigger')
    if m['has_description'] and m['desc_words'] < DESC_MIN_WORDS:
        flags.append('thin-description')
    if m['has_description'] and not m['desc_has_anti_trigger']:
        flags.append('no-anti-trigger')
    if m['body_words'] < BODY_STUB_WORDS:
        flags.append('stub-body')
    if (m['body_words'] > BODY_LONG_WORDS and m['ref_files'] == 0
            and not m['has_ref_siblings']):
        flags.append('no-progressive-disclosure')
    if m['junk_keys']:
        flags.append('nonstandard-frontmatter')
    # Informational flags (do NOT affect the overall score — they surface
    # checklist items that need a human/LLM read, not a regex verdict).
    if m['body_words'] >= BODY_STUB_WORDS and not m['has_output_format']:
        flags.append('output-format-unstated')
    if m['is_high_stakes'] and not m['has_safety_posture']:
        flags.append('high-stakes-no-safety')
    return {'overall': overall, 'grade': _grade(overall),
            'scores': scores, 'flags': flags, 'metrics': m}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python skill_quality.py path/to/SKILL.md', file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1]) as f:
        md = f.read()
    dir_name = None
    parts = sys.argv[1].replace('\\', '/').split('/')
    if len(parts) >= 2:
        dir_name = parts[-2]
    print(json.dumps(score_skill(md, dir_name), indent=2))
