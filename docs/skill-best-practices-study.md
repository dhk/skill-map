# The Skill Best-Practices Study

A measured answer to: *how should an Agent Skill be defined?* Built by scoring
every `SKILL.md` in the crawl corpus (4,902 skills across 39 repos) against the
Anthropic gold standard, three ways:

1. **By classifying all crawled skills** and grading each one.
2. **By divergence from Anthropic** — the canonical repos set the bar; everyone
   else is measured against it.
3. **By repo type** — collating findings across repos with the same signature.

## Read in this order

| Doc | What it answers |
|---|---|
| [best-practices.md](best-practices.md) | The rubric. What "good" means, derived from `anthropics/skills`. |
| [what-i-learned-crawling-39-repos.md](what-i-learned-crawling-39-repos.md) | The headline findings across the whole corpus. |
| [repo-signature-playbook.md](repo-signature-playbook.md) | "If your repo looks like X, do Y" + top-N skills to add, per signature. |
| [just-add-these-skills.md](just-add-these-skills.md) | The general-purpose set + practice-level changes for skills you already have. |
| [skill-types.md](skill-types.md) | Quality sliced by skill type — which kinds are written well vs badly. |
| [llm-judge-tuning.md](llm-judge-tuning.md) | Why the LLM judge scored Anthropic "weak," the fix, and the maturity (commit-count) finding. |

## The tooling (run it on your own repos, public or private)

| Script | Purpose |
|---|---|
| `crawlers/skill_quality.py` | Score one `SKILL.md` against the rubric. |
| `crawlers/repo_signature.py` | Classify a repo's signature from observable features. |
| `crawlers/score_corpus.py` | Score the whole crawl → `data/skill_quality.json`. |
| `crawlers/sample_llm.py` | LLM deep-read, v1 (superseded — see tuning doc). |
| `crawlers/judge_llm.py` | LLM judge **v2** — no truncation, sees reference files, per-axis scoring. |
| `crawlers/maturity_crawl.py` | Per-skill commit count vs quality (the maturity question). |
| **`crawlers/audit_repo.py`** | **Audit any repo (local or GitHub, public/private) → report + recommendations.** |

```bash
# audit your own skills against the ecosystem
python crawlers/audit_repo.py ~/.claude/skills
python crawlers/audit_repo.py --github you/private-repo --token $GITHUB_TOKEN --out audit.md
```

## The three-sentence summary

The ecosystem writes good skill **bodies** and bad skill **metadata**: 56% of
skills never tell Claude *when* to fire, and quality collapses almost entirely
inside a handful of mega-collections that hold 77% of all skills. The fix is
cheap and mechanical — two-clause descriptions, tight frontmatter, a CI quality
gate — and the single highest-leverage skill to adopt is `skill-creator`, because
it bakes the gold standard into everything you write next. If you only do one
thing: add `Use this when…` to every description.

## Reproduce

```bash
python crawlers/score_corpus.py        # heuristic pass over the corpus
python crawlers/sample_llm.py          # LLM cross-check (uses claude -p)
```

Data artifacts: `data/skill_quality.json` (per-skill + per-repo + per-signature),
`data/skill_types.json`, `data/llm_sample.json`.
