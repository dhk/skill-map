# What I Learned From Crawling 39 Skill Repos (4,902 SKILL.md files)

A heuristic quality pass over every `SKILL.md` in the corpus, scored against the
Anthropic gold standard (see [best-practices.md](best-practices.md)). One crawl,
39 repos, 4,902 skills with full content. Here is what the data says.

## The headline numbers

- **Corpus median quality: 76.2 / 100** — a solid B-minus ecosystem.
- **Grade distribution:** A 1,751 · B 1,104 · C 1,197 · D 796 · F 54.
- **Only 43% of skills tell Claude *when* to use them.** The single most common
  defect, by a wide margin: **2,770 skills have no WHEN-trigger** in their
  description.
- **Only 27% use progressive disclosure** (link to reference files instead of
  inlining everything).

## Lesson 1 — The ecosystem's quality problem is concentrated, not spread

Quality does **not** degrade evenly. It collapses in one place: **mega-collections**.

| Signature | Repos | Skills | Median quality | % with WHEN-trigger |
|---|---|---|---|---|
| canonical-reference | 5 | 118 | **89.5** | 82% |
| domain-pack | 11 | 370 | **89.0** | 74% |
| marketplace | 6 | 594 | **87.0** | 81% |
| single-skill | 7 | 7 | 87.0 | 71% |
| boutique | 5 | 38 | 84.5 | 74% |
| **mega-collection** | 5 | **3,775** | **69.4** | **33%** |

Mega-collections are **77% of all skills in the corpus** but have the lowest
median and barely a third carry a WHEN-trigger. Everything that *isn't* a
mega-collection clusters at 84–90 median. **The ecosystem median (76) is dragged
down almost entirely by five giant repos.** Curated work is genuinely good.

## Lesson 2 — The WHEN-trigger is the great divider

The biggest, cheapest, highest-leverage gap in the entire ecosystem is
descriptions that say *what* a skill does but never *when* to invoke it. This is
the text Claude reads to decide whether to use the skill at all — omitting the
trigger directly hurts retrieval.

- Canonical / domain / marketplace repos: **74–82%** have it.
- Mega-collections: **33%** have it.

Adding "Use this when…" to a description is a one-line change that moves a skill
up a full grade. It is the first thing to fix anywhere.

## Lesson 3 — Frontmatter drift is everywhere

`nonstandard-frontmatter` is the **third most common flag (1,119 skills)**. The
gold standard is disciplined: `name`, `description`, and at most `license` /
`metadata`. Out in the wild, repos sprout bespoke keys, inconsistent casing, and
`non-slug-name` values (368 skills). It rarely breaks anything, but it signals an
absent house style — and house style is exactly what separates the
canonical-reference repos from same-sized domain-packs.

## Lesson 4 — Thin descriptions are rampant

**1,732 skills (35%)** have a description under 8 words — too short to state both
what and when. Thin descriptions and missing WHEN-triggers overlap heavily and
share a fix: write a real two-clause description.

## Lesson 5 — Structure is the corpus's *strength*

Bodies are mostly fine. `stub-body` (54), `missing-description` (21), and
`missing-name` (14) are rare. People write decent skill *bodies*; what they skip
is the **frontmatter discipline and the trigger** — the parts that make a skill
*discoverable*, not just *readable*.

## Top defects across the whole corpus

| Defect | Skills affected | % of corpus |
|---|---|---|
| no WHEN-trigger | 2,770 | 56% |
| thin description (<8 words) | 1,732 | 35% |
| nonstandard frontmatter | 1,119 | 23% |
| non-slug name | 368 | 8% |
| no progressive disclosure | 248 | 5% |
| stub body | 54 | 1% |
| missing description | 21 | <1% |
| missing name | 14 | <1% |

## Lesson 6 — what the LLM cross-read caught that heuristics can't

A stratified sample of 34 skills was deep-read by Claude and compared to the
Anthropic house style (`crawlers/sample_llm.py`). **Calibration caveat:** the
judge ran *pessimistic* — it labelled even top-scoring canonical skills "weak,"
so its absolute verdicts aren't trustworthy. But its **relative** signal is
clean: every "broken" verdict landed on a genuinely low-scoring skill (heuristic
< 50), while higher scores got "weak," never "broken." The heuristic floor and
the LLM floor agree.

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

The Claude skills ecosystem writes good *content* and bad *metadata*. Bodies are
structured and useful; descriptions too often fail to say when to fire, and
frontmatter drifts from the canonical shape. The fix is overwhelmingly cheap —
two-clause descriptions and a tight frontmatter schema — and it is concentrated
in a handful of mega-collections that, if they adopted a CI quality gate, would
lift the entire ecosystem median by double digits.

---

*Generated by `crawlers/score_corpus.py` over `crawls/crawl-1-2026-06-24`.
Reproduce: `python crawlers/score_corpus.py`.*
