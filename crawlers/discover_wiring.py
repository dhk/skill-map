#!/usr/bin/env python3
"""
discover_wiring.py — mine the skill corpus for implicit inter-skill wiring.

Extracts three signal types from every SKILL.md body and description:
  1. Slash-command references  (/skill-name, /tool-name)
  2. Explicit sequential cues  (after/before/requires/use X skill)
  3. Known-name mentions       (any corpus skill name that appears in another skill's content)

Produces:
  data/skill_wiring.json       — edge list with evidence snippets
  data/skill_clusters.json     — co-occurrence clusters within each repo
  docs/skill-wiring-study.md   — findings document

Usage:
  python crawlers/discover_wiring.py [--crawl PATH] [--out-dir data/]
"""

import json
import re
import argparse
import collections
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

SLASH_RE = re.compile(r'/([a-z][a-z0-9-]{2,})', re.IGNORECASE)

SEQUENTIAL_RE = re.compile(
    r'\b(?:after|before|requires?|depends? on|use (?:the )?|run |invoke |with (?:the )?)'
    r'[`"\']?([a-z][a-z0-9-]{2,})[`"\']?'
    r'(?:\s+(?:skill|first|next|prior|previously|command|tool))?',
    re.IGNORECASE,
)

# Patterns that indicate explicit orchestration / coordinator role
ORCHESTRATOR_RE = re.compile(
    r'\b(?:coordinates?|orchestrates?|chains?|pipeline|workflow|handoff|passes? (?:output|context|results?) to'
    r'|invokes?|calls?|triggers?|spawns?)\b',
    re.IGNORECASE,
)

# Explicit "Do NOT use when X has/hasn't run" gating patterns
GATE_RE = re.compile(
    r'(?:do not use when|not use if|only (?:after|once|when)|requires? .*(?:to have run|first))',
    re.IGNORECASE,
)

CONTEXT_WINDOW = 80  # chars of surrounding text to capture as evidence


def extract_context(text, match):
    start = max(0, match.start() - CONTEXT_WINDOW // 2)
    end = min(len(text), match.end() + CONTEXT_WINDOW // 2)
    snippet = text[start:end].replace('\n', ' ').strip()
    return f'…{snippet}…'


def skill_name_from_path(path: str) -> str:
    parts = path.replace('\\', '/').split('/')
    if len(parts) >= 2 and parts[-1].upper() == 'SKILL.MD':
        return parts[-2].lower()
    return ''


def load_corpus(crawl_path: str) -> list[dict]:
    with open(crawl_path) as f:
        data = json.load(f)
    results = data.get('results', data) if isinstance(data, dict) else data
    return [r for r in results if r.get('skill_md_content') and not r.get('fetch_error')]


# ---------------------------------------------------------------------------
# main discovery
# ---------------------------------------------------------------------------

def discover(skills: list[dict]) -> tuple[list[dict], dict]:
    # Build lookup: name -> list of (repo, path) for disambiguation
    name_index: dict[str, list[str]] = collections.defaultdict(list)
    for s in skills:
        n = skill_name_from_path(s['file_path'])
        if n:
            name_index[n].append(s['repo_full_name'])

    known_names = set(name_index.keys())

    edges: list[dict] = []
    repo_skills: dict[str, list[str]] = collections.defaultdict(list)

    for s in skills:
        src_name = skill_name_from_path(s['file_path'])
        if not src_name:
            continue
        repo = s['repo_full_name']
        repo_skills[repo].append(src_name)

        content = s['skill_md_content']
        seen_targets: set[str] = set()

        # --- signal 1: slash commands ---
        for m in SLASH_RE.finditer(content):
            target = m.group(1).lower()
            if target != src_name and target in known_names and target not in seen_targets:
                seen_targets.add(target)
                edges.append({
                    'source': src_name,
                    'source_repo': repo,
                    'target': target,
                    'target_repos': name_index[target],
                    'signal': 'slash_command',
                    'evidence': extract_context(content, m),
                })

        # --- signal 2: sequential cues ---
        for m in SEQUENTIAL_RE.finditer(content):
            target = m.group(1).lower()
            if target != src_name and target in known_names and target not in seen_targets:
                seen_targets.add(target)
                edges.append({
                    'source': src_name,
                    'source_repo': repo,
                    'target': target,
                    'target_repos': name_index[target],
                    'signal': 'sequential_cue',
                    'evidence': extract_context(content, m),
                })

        # --- signal 3: known-name mentions (body text only, not title) ---
        # Strip frontmatter to avoid spurious self-matches in name: field
        body = re.sub(r'^---.*?---', '', content, flags=re.DOTALL).lower()
        # Prefilter: only check names whose first token appears in body (fast substring)
        for name in known_names:
            if name == src_name or name in seen_targets:
                continue
            # Only hyphenated names — single-word "names" are too generic to be signal
            if '-' not in name:
                continue
            if len(name) < 5:
                continue
            # Fast precheck before regex
            if name not in body:
                continue
            # whole-word match
            pat = r'\b' + re.escape(name) + r'\b'
            m = re.search(pat, body)
            if m:
                seen_targets.add(name)
                edges.append({
                    'source': src_name,
                    'source_repo': repo,
                    'target': name,
                    'target_repos': name_index[name],
                    'signal': 'name_mention',
                    'evidence': body[max(0, m.start()-60):m.end()+60].replace('\n', ' ').strip(),
                })

        # --- orchestrator flag ---
        if ORCHESTRATOR_RE.search(content):
            edges_for_src = [e for e in edges if e['source'] == src_name]
            for e in edges_for_src:
                e['orchestrator'] = True

    return edges, dict(repo_skills)


# ---------------------------------------------------------------------------
# cluster: within each repo, find skills that reference each other (cliques)
# ---------------------------------------------------------------------------

def find_clusters(edges: list[dict], repo_skills: dict) -> list[dict]:
    # Adjacency within same repo
    adj: dict[str, set[str]] = collections.defaultdict(set)
    for e in edges:
        if e['source_repo'] in repo_skills:
            # Only intra-repo edges for clusters
            if e['target'] in repo_skills.get(e['source_repo'], []):
                adj[e['source']].add(e['target'])
                adj[e['target']].add(e['source'])

    # Simple connected-component extraction
    visited: set[str] = set()
    clusters = []
    for node in list(adj.keys()):
        if node in visited:
            continue
        component: set[str] = set()
        queue = [node]
        while queue:
            n = queue.pop()
            if n in visited:
                continue
            visited.add(n)
            component.add(n)
            queue.extend(adj[n] - visited)
        if len(component) >= 2:
            clusters.append(sorted(component))

    return sorted(clusters, key=len, reverse=True)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def write_study(edges: list[dict], clusters: list[list[str]], out_path: str):
    total = len(edges)
    by_signal = collections.Counter(e['signal'] for e in edges)
    orchestrators = {e['source'] for e in edges if e.get('orchestrator')}

    # Top referenced targets
    target_counts = collections.Counter(e['target'] for e in edges)
    top_targets = target_counts.most_common(20)

    # Cross-repo edges
    cross_repo = [e for e in edges
                  if e['source_repo'] not in e['target_repos']]

    # Strong edges (slash_command or sequential_cue, not just name mention)
    strong = [e for e in edges if e['signal'] in ('slash_command', 'sequential_cue')]

    lines = [
        "# Skill Wiring: Implicit Integration Patterns in the Corpus",
        "",
        f"*Discovered from {total:,} cross-skill references across the crawl corpus.*",
        "",
        "---",
        "",
        "## Overview",
        "",
        "This study mines the skill corpus for implicit wiring: references from one skill's",
        "body or description to another skill by name or slash-command. No new standard is",
        "assumed — these are patterns that exist today, undeclared.",
        "",
        "Three signal types were extracted:",
        "",
        "| Signal | Edges found | Description |",
        "|---|---|---|",
        f"| Slash-command reference (`/skill-name`) | {by_signal['slash_command']:,} | Explicit invocation syntax in body |",
        f"| Sequential cue (after/before/requires) | {by_signal['sequential_cue']:,} | Ordering language referencing a known skill |",
        f"| Known-name mention | {by_signal['name_mention']:,} | Corpus skill name appearing in another skill's body |",
        f"| **Total** | **{total:,}** | |",
        "",
        "---",
        "",
        "## Key findings",
        "",
        f"**{len(strong):,} strong wiring edges** (slash-command or sequential cue) across the corpus.",
        f"**{len(cross_repo):,} cross-repo edges** — skills in one repo referencing skills defined in another.",
        f"**{len(orchestrators)} orchestrator candidates** — skills whose bodies contain coordination language",
        "(\"coordinates\", \"chains\", \"pipeline\", \"handoff\", \"invokes\").",
        f"**{len(clusters)} intra-repo clusters** — groups of 2+ skills that mutually reference each other.",
        "",
        "---",
        "",
        "## Most-referenced skills",
        "",
        "Skills referenced most frequently by other skills — the hubs of the implicit wiring graph.",
        "",
        "| Skill | Referenced by (edges) |",
        "|---|---|",
    ]
    for name, count in top_targets:
        lines.append(f"| `{name}` | {count} |")

    lines += [
        "",
        "---",
        "",
        "## Orchestrator candidates",
        "",
        "Skills that contain explicit coordination language and reference two or more other skills.",
        "",
    ]
    orch_with_targets = {
        name: [e['target'] for e in edges if e['source'] == name]
        for name in sorted(orchestrators)
    }
    if orch_with_targets:
        lines.append("| Orchestrator skill | References |")
        lines.append("|---|---|")
        for name, targets in sorted(orch_with_targets.items(), key=lambda x: -len(x[1]))[:30]:
            lines.append(f"| `{name}` | {', '.join(f'`{t}`' for t in targets[:6])} |")
    else:
        lines.append("*None detected with current patterns.*")

    lines += [
        "",
        "---",
        "",
        "## Intra-repo wiring clusters",
        "",
        f"Top {min(20, len(clusters))} clusters of mutually referencing skills within a single repo.",
        "",
        "| Size | Skills |",
        "|---|---|",
    ]
    for cluster in clusters[:20]:
        lines.append(f"| {len(cluster)} | {', '.join(f'`{s}`' for s in cluster)} |")

    lines += [
        "",
        "---",
        "",
        "## Cross-repo wiring (sample)",
        "",
        "Skills in one repository explicitly referencing skills defined in another — the clearest",
        "signal of emergent ecosystem-level integration.",
        "",
        "| Source repo | Source skill | → Target skill | Target repo(s) | Signal |",
        "|---|---|---|---|---|",
    ]
    for e in [x for x in cross_repo if x['signal'] != 'name_mention'][:30]:
        target_repos = ', '.join(e['target_repos'][:2])
        lines.append(
            f"| `{e['source_repo']}` | `{e['source']}` | `{e['target']}` | `{target_repos}` | {e['signal']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## What this implies",
        "",
        "The corpus already contains an implicit wiring layer — skills reference each other by",
        "slash-command syntax and sequential language, forming chains and clusters that no",
        "published standard captures. The patterns fall into three types:",
        "",
        "**1. Sequential pipelines** — skill A says \"after running /skill-B\"; ordering is",
        "   declared unilaterally by one skill, invisible to the other.",
        "",
        "**2. Coordinator skills** — one skill orchestrates several others by naming them",
        "   explicitly; the sub-skills have no awareness of the coordinator.",
        "",
        "**3. Ecosystem hubs** — a small number of skills (see most-referenced table) are",
        "   referenced widely across unrelated repos, suggesting emergent standards.",
        "",
        "None of these wirings are machine-readable. A consumer of the corpus has no way to",
        "discover that skill A depends on skill B except by reading prose. This is the gap",
        "a `wiring.md` convention would close.",
        "",
        "---",
        "",
        "*Generated by `crawlers/discover_wiring.py`. Re-run to refresh.*",
    ]

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"Wrote {out_path}")


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crawl', default='crawls/crawl-3-2026-06-28/data.json',
                        help='Path to crawl data.json')
    parser.add_argument('--out-dir', default='data/', help='Output directory for JSON files')
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    crawl_path = repo_root / args.crawl
    out_dir = repo_root / args.out_dir

    print(f"Loading corpus from {crawl_path}…")
    skills = load_corpus(str(crawl_path))
    print(f"  {len(skills):,} skills with content")

    print("Discovering wiring…")
    edges, repo_skills = discover(skills)
    print(f"  {len(edges):,} edges found")

    clusters = find_clusters(edges, repo_skills)
    print(f"  {len(clusters)} intra-repo clusters")

    out_dir.mkdir(parents=True, exist_ok=True)

    wiring_path = out_dir / 'skill_wiring.json'
    with open(wiring_path, 'w') as f:
        json.dump(edges, f, indent=2)
    print(f"Wrote {wiring_path}")

    clusters_path = out_dir / 'skill_clusters.json'
    with open(clusters_path, 'w') as f:
        json.dump(clusters, f, indent=2)
    print(f"Wrote {clusters_path}")

    study_path = repo_root / 'docs' / 'skill-wiring-study.md'
    write_study(edges, clusters, str(study_path))


if __name__ == '__main__':
    main()
