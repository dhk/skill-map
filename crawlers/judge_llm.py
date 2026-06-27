"""
judge_llm.py — Tuned LLM judge (v2) for SKILL.md quality.

Replaces the v1 judge in sample_llm.py, which scored even canonical Anthropic
skills as "weak". Post-mortem (see docs/llm-judge-tuning.md) found three causes,
two of them harness bugs:

  1. TRUNCATION — v1 clipped every skill to 6000 chars, so the judge penalised
     long (often best) skills for being "truncated mid-sentence". FIX: pass the
     full file; only clip at a high bound and tell the model when we did.
  2. NO REFERENCE-FILE VISIBILITY — the crawl only fetched SKILL.md, so the judge
     assumed "inline == no progressive disclosure" even when the skill folder has
     reference/ and scripts/ dirs (it usually does). FIX: fetch the skill's
     sibling file listing and give it to the judge.
  3. NO CALIBRATION ANCHOR — v1 asked for one holistic verdict against four high
     bars with no exemplar, so the model defaulted pessimistic. FIX: per-axis
     0–10 scoring with explicit anchors + a one-shot exemplar.

Usage:
    python crawlers/judge_llm.py --validate          # re-judge the canonical
                                                     #   skills to prove recovery
    python crawlers/judge_llm.py --n 2               # stratified sample
    python crawlers/judge_llm.py --dry-run
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).parent.parent
CRAWL = BASE / 'crawls' / 'crawl-1-2026-06-24' / 'data.json'
SCORES = BASE / 'data' / 'skill_quality.json'
OUT = BASE / 'data' / 'llm_sample_v2.json'

MAX_CHARS = 32000   # high enough that real skills are never clipped

# Per-axis anchors keep the model from collapsing everything to "weak".
PROMPT = """You are grading an Agent Skill's SKILL.md against Anthropic's house \
style. Score each axis 0–10 using these anchors:
  9–10 = matches or exceeds anthropics/skills
  7–8  = solid, minor gaps
  5–6  = usable but clearly diverges
  3–4  = significant problems
  0–2  = broken/placeholder
A well-formed canonical skill should score 8–10 on most axes. Do NOT default to
low scores; reserve 0–4 for genuine defects.

IMPORTANT: progressive disclosure is satisfied when depth lives in sibling files
(reference/, scripts/, *.md) — the file listing below tells you what exists.
Inlining is only a problem when NO such files exist. Judge completeness on the
content given; it is the full file unless marked [CLIPPED].

Reference exemplar (scores ~9–10): a skill whose description states WHAT it does
and WHEN to use it in 2–4 sentences, with an anti-trigger note; a body with clear
headings and a worked example; heavy detail delegated to reference/ files.

Axis definitions (the last three need real judgment, not pattern-matching):
  scope        — one clear job, narrow & reliable, doesn't sprawl into a catch-all
  instruction  — top instructions short & unambiguous; says what to DO (not just
                 what to avoid); output format explicit; constraints stated early
  safety       — for risky/high-stakes work (deploy, delete, payments, prod): are
                 there validation steps, tight constraints, deterministic scripts,
                 or appropriate model-invocation controls? (N/A → score 8 if the
                 skill is low-stakes and needs none)

Reply with ONLY this JSON, no prose:
{{"axes":{{"frontmatter":0-10,"triggering":0-10,"disclosure":0-10,"structure":0-10,"tone":0-10,"scope":0-10,"instruction":0-10,"safety":0-10}},
  "overall":"exemplary|solid|weak|broken",
  "genuine_issues":["only real, non-artifact problems"],
  "best_trait":"short phrase"}}

Repo: {repo}  (signature: {signature})
Files in this skill's folder: {siblings}
--- SKILL.md{clip} ---
{md}
--- end ---"""

_sibling_cache = {}


def fetch_siblings(repo, file_path):
    """List files in the skill's folder + one level into reference/scripts dirs."""
    key = (repo, file_path)
    if key in _sibling_cache:
        return _sibling_cache[key]
    owner_repo = repo
    d = '/'.join(file_path.replace('\\', '/').split('/')[:-1])
    url = f'https://api.github.com/repos/{owner_repo}/contents/{d}'
    names = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'skill-map'})
        items = json.loads(urllib.request.urlopen(req, timeout=30).read())
        for it in items:
            names.append(it['name'] + ('/' if it['type'] == 'dir' else ''))
            if it['type'] == 'dir' and it['name'] in ('reference', 'references',
                                                      'scripts', 'assets'):
                try:
                    sub = json.loads(urllib.request.urlopen(
                        urllib.request.Request(it['url'],
                                               headers={'User-Agent': 'skill-map'}),
                        timeout=30).read())
                    names += [f"{it['name']}/{s['name']}" for s in sub[:12]]
                except Exception:
                    pass
    except Exception as e:
        names = [f'(could not list: {e.__class__.__name__})']
    res = ', '.join(names) if names else '(only SKILL.md)'
    _sibling_cache[key] = res
    return res


def call_claude(prompt):
    r = subprocess.run(['claude', '-p', prompt],
                       capture_output=True, text=True, timeout=240)
    out = r.stdout.strip()
    a, b = out.find('{'), out.rfind('}')
    if a >= 0 and b > a:
        try:
            return json.loads(out[a:b + 1])
        except json.JSONDecodeError:
            pass
    return {'error': 'unparseable', 'raw': out[:300]}


def judge_one(repo, file_path, md, signature):
    siblings = fetch_siblings(repo, file_path)
    clip = ''
    if len(md) > MAX_CHARS:
        md = md[:MAX_CHARS]
        clip = ' [CLIPPED — judge content as given, do not penalise length]'
    prompt = PROMPT.format(repo=repo, signature=signature, siblings=siblings,
                           clip=clip, md=md)
    res = call_claude(prompt)
    if 'axes' in res:
        ax = res['axes']
        res['axis_mean'] = round(sum(ax.values()) / len(ax), 2)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--validate', action='store_true',
                    help='re-judge canonical skills to demonstrate recovery')
    ap.add_argument('--n', type=int, default=2)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    scores = json.load(open(SCORES))
    crawl = {(r['repo_full_name'], r['file_path']): r
             for r in json.load(open(CRAWL))['results']
             if r.get('skill_md_content')}
    repo_sig = {rn: r['signature'] for rn, r in scores['repos'].items()}

    if args.validate:
        targets = [s for s in scores['skills']
                   if s['repo'] in ('anthropics/skills', 'openai/skills')]
    else:
        import random
        random.seed(7)
        buckets = {}
        for s in scores['skills']:
            sig = repo_sig[s['repo']]
            tier = ('high' if s['overall'] >= 80 else
                    'low' if s['overall'] < 60 else 'mid')
            buckets.setdefault((sig, tier), []).append(s)
        targets = []
        for items in buckets.values():
            targets += random.sample(items, min(args.n, len(items)))

    path = OUT if not args.validate else BASE / 'data' / 'llm_validate_v2.json'
    # resilient: load any prior results and write after each judgment
    results = json.load(open(path))['results'] if path.exists() else []
    seen = {(r['repo'], r['file_path']) for r in results}

    print(f'judging {len(targets)} skills (v2); {len(seen)} already cached')
    for s in targets:
        key = (s['repo'], s['file_path'])
        if key in seen:
            continue
        md = crawl[key]['skill_md_content']
        sig = repo_sig[s['repo']]
        if args.dry_run:
            print(f'  would judge {s["repo"]}/{s["file_path"]} '
                  f'({len(md)} chars) sibs={fetch_siblings(*key)[:80]}')
            continue
        res = judge_one(s['repo'], s['file_path'], md, sig)
        results.append({'repo': s['repo'], 'file_path': s['file_path'],
                        'signature': sig, 'heuristic_score': s['overall'],
                        'llm': res})
        Path(path).write_text(json.dumps({'results': results}, indent=1))
        _p = s['file_path'].replace('\\', '/').split('/')
        nm = _p[-2] if len(_p) >= 2 else _p[-1]
        print(f'  {s["repo"][:24]:24s} {nm[:20]:20s} '
              f'h={s["overall"]:.0f} → {res.get("overall","?")} '
              f'(axis_mean={res.get("axis_mean","?")})')

    if not args.dry_run:
        print(f'wrote {path} ({len(results)} judged)')


if __name__ == '__main__':
    main()
