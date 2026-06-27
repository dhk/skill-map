# What I Learned From Crawling 39 Skill Repos (4,902 SKILL.md files)

A heuristic quality pass over every `SKILL.md` in the corpus, scored against the
Anthropic gold standard (see [best-practices.md](best-practices.md)). One crawl,
39 repos, 4,902 skills with full content. Here is what the data says.

## The headline numbers

- **Corpus median quality: 79.8 / 100** — a solid B ecosystem, better than first
  reported (see the correction note below).
- **Grade distribution:** A 1,574 · B 2,430 · C 766 · D 78 · F 54.
- **Only 2.5% of skills state when *not* to use them** (the anti-trigger note) —
  the rarest practice in the ecosystem and the #1 defect (4,758 skills). Even the
  canonical repos almost all miss it. This is the one genuinely universal gap.
- **68% tell Claude *when* to use them** — 1,521 skills still have no
  WHEN-trigger, but most do.
- **Only 27% use progressive disclosure** (link to reference files instead of
  inlining everything).

> **Correction (parser fix).** An earlier pass reported median 73.5 and "only
> 43% have a WHEN-trigger." That was a bug: the scorer didn't parse YAML
> block-scalar descriptions (`description: |-`), which **27.5% of the corpus
> uses** — so a quarter of all skills had their descriptions read as empty. After
> fixing it, the median rose to 79.8 and WHEN-triggers to 68%. The lesson cuts
> both ways: measure your measurement. The anti-trigger finding survived; the
> "ecosystem writes bad metadata" narrative softened to "the ecosystem is fine
> except for one near-universal omission."

## Lesson 1 — The ecosystem's quality problem is concentrated, not spread

Quality does **not** degrade evenly. It collapses in one place: **mega-collections**.

| Signature | Repos | Skills | Median quality | % with WHEN-trigger |
|---|---|---|---|---|
| canonical-reference | 5 | 118 | **85.0** | 87% |
| domain-pack | 11 | 370 | **85.0** | 81% |
| marketplace | 6 | 594 | **85.0** | 87% |
| single-skill | 7 | 7 | 85.0 | 100% |
| boutique | 5 | 38 | 80.0 | 87% |
| **mega-collection** | 5 | **3,775** | **78.0** | **64%** |

Mega-collections are **77% of all skills in the corpus** and have the lowest
median (78) and the lowest WHEN-trigger rate (64%). Everything that *isn't* a
mega-collection clusters at 80–85 median. The gap is real but **modest** — these
are big aggregations with uneven contributions, not junk. Curated work is a notch
better across the board.

## Lesson 2 — The WHEN-trigger still divides curated from bulk

The cheapest, highest-leverage gap is descriptions that say *what* a skill does
but never *when* to invoke it. Two-thirds of the corpus gets this right; the
shortfall is concentrated in mega-collections. This is
the text Claude reads to decide whether to use the skill at all — omitting the
trigger directly hurts retrieval.

- Canonical / domain / marketplace repos: **81–87%** have it.
- Mega-collections: **64%** have it.

Adding "Use this when…" to a description is a one-line change that moves a skill
up a full grade. It is the first thing to fix anywhere.

## Lesson 3 — Frontmatter drift is everywhere

`nonstandard-frontmatter` is the **third most common flag (1,119 skills)**. The
gold standard is disciplined: `name`, `description`, and at most `license` /
`metadata`. Out in the wild, repos sprout bespoke keys, inconsistent casing, and
`non-slug-name` values (368 skills). It rarely breaks anything, but it signals an
absent house style — and house style is exactly what separates the
canonical-reference repos from same-sized domain-packs.

## Lesson 4 — Thin descriptions are rare (once you parse them right)

Only **388 skills (8%)** have a description under 8 words. An earlier pass put
this at 35% — almost all of that was the block-scalar parser bug reading real
multi-line descriptions as empty. Genuinely thin descriptions are the exception.

## Lesson 5 — Structure is the corpus's *strength*

Bodies are mostly fine. `stub-body` (54), `missing-description` (21), and
`missing-name` (14) are rare. People write decent skill *bodies*; what they skip
is the **frontmatter discipline and the trigger** — the parts that make a skill
*discoverable*, not just *readable*.

## Top defects across the whole corpus

| Defect | Skills affected | % of corpus |
|---|---|---|
| no anti-trigger ("when NOT to use") | 4,758 | 97% |
| no WHEN-trigger | 1,521 | 31% |
| thin description (<8 words) | 388 | 8% |
| nonstandard frontmatter | 1,119 | 23% |
| non-slug name | 368 | 8% |
| no progressive disclosure | 248 | 5% |
| stub body | 54 | 1% |
| missing description | 21 | <1% |
| missing name | 14 | <1% |

## Lesson 6 — what the LLM cross-read caught that heuristics can't

A stratified sample was deep-read by Claude and compared to the Anthropic house
style. The first judge (`sample_llm.py`) was miscalibrated and called even
Anthropic "weak"; the **tuned v2 judge** (`judge_llm.py`, see
[llm-judge-tuning.md](llm-judge-tuning.md)) agrees with the heuristic cleanly and
monotonically:

| Heuristic band | v2 verdicts |
|---|---|
| < 50 | broken ×3, weak ×1 |
| 50–75 | solid ×9, exemplary ×1, weak ×2 |
| 75–90 | solid ×9, exemplary ×1, weak ×2 |
| 90+ | exemplary ×2, solid ×2 |

The two graders now track each other — the LLM adds *substance* judgment on top of
the heuristic's *structure* check. Its weakest axes across the sample are
**triggering (6.2/10)** and **disclosure (6.2)**, exactly the dimensions the
corpus numbers flag.

Where it earned its keep was the **qualitative divergences** structure can't see:

- **No progressive disclosure / no reference links** (most common) — rulebooks
  dumped inline instead of linked out.
- **No concrete examples** — passes the heading check, still unhelpful.
- **Unbounded triggers** — "use in any conversation" is technically a trigger
  but a meaningless one.
- **Coercive tone** — "absolutely must," "you do not have a choice," "not
  negotiable," adversarial "red flags" tables that frame the model as a threat to
  be guarded against. This clashes hard with Anthropic's measured, collaborative
  voice.
- **Non-standard XML-ish tags** (`<extremely-important>`, `<subagent-stop>`) with
  no canonical precedent.
- **Scope creep** — "personality configuration" (gratitude bans, tone policing)
  smuggled in as skill content; meta-governance conflated with task guidance.
- **Unshippable artifacts** — at least one file truncated mid-sentence.

The lesson: a high structural score is necessary, not sufficient. Use the
heuristic as a fast gate; use a qualitative read to catch tone, scope, and
substance.

## The one-paragraph takeaway

The Claude skills ecosystem is in better shape than headlines suggest: median
~80, two-thirds of skills carry a WHEN-trigger, bodies are structured and useful.
The one near-universal omission is the **anti-trigger note** — 97% of skills
never say when *not* to fire. That, plus some frontmatter drift in the
mega-collections, is the whole to-do list. The fix is cheap and mechanical.

---

*Generated by `crawlers/score_corpus.py` over `crawls/crawl-1-2026-06-24`.
Reproduce: `python crawlers/score_corpus.py`.*
