# Vulnerabilities, Anti-Patterns, and Best Practices in Published Claude Agent Skills

*A corpus analysis of 4,953 SKILL.md files across 41 public repositories.*

---

## Overview

This document reports findings from a systematic quality assessment of the Claude
Agent Skills ecosystem. Every `SKILL.md` in the crawl corpus was scored against
the Anthropic canonical standard using a five-axis rubric (frontmatter, triggering,
disclosure, structure, safety — see
[rubric.md](../plugins/skill-doctor/skills/skill-doctor/reference/rubric.md)).
A stratified sample was additionally reviewed by a calibrated LLM judge. Corpus
coverage: 41 repositories, 4,953 skills with full content, crawled June 2026.

The headline finding is a system that is structurally competent but has a single
near-universal vulnerability — the missing anti-trigger — and a smaller but more
serious cluster of safety defects in tool scoping and data handling.

---

## Corpus composition

| Repository type | Repos | Skills | Share |
|---|---|---|---|
| Mega-collection | 5 | 3,775 | 77% |
| Marketplace | 6 | 594 | 12% |
| Domain-pack | 12 | 410 | 8% |
| Canonical-reference | 5 | 118 | 2% |
| Boutique | 6 | 49 | 1% |
| Single-skill | 7 | 7 | <1% |

Mega-collections — large aggregations of skills from multiple contributors — dominate
the corpus numerically. This has direct implications for where defects concentrate.

---

## Quality distribution

| Grade | Score range | Skills | % |
|---|---|---|---|
| A | ≥ 85 | 2,033 | 41% |
| B | 70–84 | 2,100 | 42% |
| C | 55–69 | 690 | 14% |
| D | 40–54 | 76 | 2% |
| F | < 40 | 54 | 1% |

**Corpus median: 82.5 / 100.** The distribution is left-skewed: the majority of
skills are structurally sound. The long tail — ~17% graded C or below — is
concentrated almost entirely in mega-collections and is driven by a small number
of recurring defects rather than broad-based quality failure.

---

## Defect inventory

The table below ranks every flagged defect by prevalence across the full corpus.

| Defect | Skills affected | % of corpus |
|---|---|---|
| No anti-trigger ("Do NOT use when…") | 4,758 | **97%** |
| No WHEN-trigger ("Use this when…") | 1,521 | 31% |
| Nonstandard frontmatter keys | 1,119 | 23% |
| Thin description (< 8 words) | 388 | 8% |
| Non-slug `name` field | 368 | 8% |
| No progressive disclosure (reference files) | 248 | 5% |
| Stub body | 54 | 1% |
| Missing description | 21 | < 1% |
| Missing name | 14 | < 1% |

### The dominant defect: missing anti-trigger (97%)

The anti-trigger — a clause stating *when not to invoke* a skill — is the rarest
practice in the ecosystem and the highest-leverage fix. Without it, the model has
no signal to suppress the skill in adjacent contexts: a code-review skill fires on
refactoring requests; a deployment skill activates on read-only queries.

The defect is near-universal across all repository types, including canonical
references. It is also the cheapest fix: one clause added to the `description`
field.

### Secondary defect: missing WHEN-trigger (31%)

The WHEN-trigger — a clause stating *when to invoke* — is the mechanism by which
the model routes to a skill at all. It is absent in 31% of the corpus. The rate
splits sharply by repository type: 87% of canonical and marketplace repos include
it; 64% of mega-collections do. The shortfall is concentrated in bulk-aggregated
content where descriptions function as capability blurbs rather than invocation
cues.

### Structural defects: frontmatter drift

Nonstandard frontmatter (23%) and non-slug names (8%) are prevalent but low-impact
in isolation. Their significance is diagnostic: they indicate an absent authoring
standard. Canonical repositories that enforce house style score 87–90 on the
rubric; those that do not cluster around 80. The correlation is reliable.

---

## Safety vulnerabilities

The defects above affect *discoverability and routing*. The following affect
*safety*. They are less prevalent but higher severity.

### Unscoped tool grants

16% of the corpus declares `allowed-tools`. Of those, **more than 50% grant bare
`Bash`** — unrestricted shell access — rather than a scoped pattern (e.g.
`Bash(git log*)`, `Bash(npm run*)`). The scoped and unscoped variants differ
significantly in blast radius: a bare `Bash` grant permits arbitrary command
execution; a scoped pattern restricts it to the intended operation.

Skills that take agentic actions — file edits, deployments, database operations —
should declare `allowed-tools` at the narrowest scope that still works. Skills that
only produce content (documentation, analysis) generally do not need tool
declarations.

### Sensitive data without safeguards

376 skills in the corpus reference regulated or sensitive data: HIPAA, PHI, PII,
GDPR, patient records, SSNs, financial data. **Only 48% of those include any data
handling guidance.** The remaining 52% instruct the model to process sensitive
data with no stated safeguards: no redaction, no retention policy, no handling of
credentials or secrets.

The absence of a data handling section is not a soft quality issue. In regulated
domains it is a compliance gap. The required content is straightforward: what data
the skill reads or writes, any de-identification before processing, explicit
prohibition on logging or echoing sensitive values, and applicable locale
constraints (HIPAA, GDPR).

### High-stakes actions without confirmation guards

Approximately 50% of the corpus references irreversible or costly operations:
deploy, delete, drop, migrate, payments, production. Of those, a significant share
have no explicit guard — no dry-run step, no explicit confirmation prompt, no
validation before execution. Irreversible actions that proceed without a
confirmation step expose users to data loss or unintended side effects with no
recovery path.

---

## LLM cross-validation

A stratified sample was reviewed by a calibrated LLM judge (see
[llm-judge-tuning.md](llm-judge-tuning.md)). The judge agreed with the heuristic
scorer monotonically across score bands:

| Heuristic band | LLM verdicts |
|---|---|
| < 50 | broken ×3, weak ×1 |
| 50–75 | solid ×9, exemplary ×1, weak ×2 |
| 75–90 | solid ×9, exemplary ×1, weak ×2 |
| 90+ | exemplary ×2, solid ×2 |

The LLM review surfaced qualitative defects the heuristic cannot detect:

- **Unbounded triggers** — "use in any conversation" passes the presence check but
  provides no routing signal.
- **Coercive tone** — adversarial framing ("you do not have a choice," "red flags"
  tables treating the model as a threat) that conflicts with Anthropic's
  collaborative authoring voice and degrades model compliance.
- **Scope creep** — personality configuration, tone policing, and meta-governance
  smuggled into skill content.
- **Non-standard markup** — proprietary XML-ish tags (`<extremely-important>`,
  `<subagent-stop>`) with no canonical precedent and undefined behavior.
- **Truncated artifacts** — at least one published skill in the corpus is
  truncated mid-sentence.
- **Concrete examples absent** — passes the structural heading check but provides
  no worked example, making the skill harder to invoke correctly.

A high structural score is necessary but not sufficient. The heuristic functions
as a fast gate; qualitative review catches tone, scope, and substance failures.

---

## What the data implies for the ecosystem

**The core problem is not quality — it is the absence of a shared standard.**

The ecosystem median (82.5) is respectable. Bodies are well-written. Most skills
have a purpose and execute it. The defects that exist are not evidence of
careless authorship; they are evidence that authors have no canonical checklist to
work from. The anti-trigger is absent from 97% of skills not because authors
disagree with the practice but because the practice has not been articulated as a
norm.

The safety vulnerabilities — unscoped tools, unguarded sensitive data, missing
confirmation steps — follow the same pattern. They appear most often in domain
areas (infrastructure, healthcare, finance) where the stakes are highest and the
existing guidance is thinnest.

---

## What we are going to do about it

Three interventions, in order of leverage:

**1. Individual skill review: skill-doctor**

An interactive reviewer that audits a single `SKILL.md` against the rubric, runs
a structured interview for context the file cannot provide (tool scoping rationale,
data sensitivity, intended trigger scope), and recommends concrete edits. It
applies fixes on explicit confirmation. Addresses the full defect set including
safety.

Install in Claude Code:
```
/plugin marketplace add dhk/skill-map
/plugin install skill-doctor@skill-map
```

**2. Repository-level audit: audit_repo.py / skill-audit Action**

A programmatic auditor that scores an entire repo, benchmarks it against same-type
peers in the corpus, surfaces the worst offenders, and identifies overlapping
skills to consolidate. Runs locally or as a GitHub Action that comments on every
PR touching a `SKILL.md`.

```bash
python crawlers/audit_repo.py --github owner/repo
```

```yaml
- uses: dhk/skill-map/.github/actions/skill-audit@main
```

**3. Ecosystem visibility: the skill map**

A continuously updated index of the public skills ecosystem, graded and searchable,
that makes quality and provenance visible at the repository level. Authors can
submit their repos for inclusion; the crawler re-scores on each crawl.

[dhk.github.io/skill-map](https://dhk.github.io/skill-map)

---

*Source data: `crawlers/score_corpus.py` over `crawls/` (crawl-1 + crawl-2).
Reproduce with `python crawlers/score_corpus.py`. Rubric:
[reference/rubric.md](../plugins/skill-doctor/skills/skill-doctor/reference/rubric.md).
LLM judge methodology: [llm-judge-tuning.md](llm-judge-tuning.md).*
