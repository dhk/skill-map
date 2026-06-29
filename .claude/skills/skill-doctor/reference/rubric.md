# The rubric (self-contained)

Derived from `anthropics/skills` and validated against a crawl of ~5,000
`SKILL.md` files across 40+ repos. Five axes; the first four are quality, the
fifth is safety. A skill that scores well on 1–4 but fails 5 is **not**
best-practice.

Score each axis 0–100, then weight: frontmatter 20 · triggering 25 ·
disclosure 15 · structure 15 · safety 25.

## 1. Frontmatter (20%)
- `name` present and **equals the skill's directory name** (99% of elite skills;
  64% of the rest — a reliable tell).
- `description` present, **14–80 words**, two clauses: *what it does* + *when to
  use it*.
- `license` is common in canonical repos; `version` optional.
- **Red flag:** `origin` / `source` provenance keys usually mark copied/aggregated
  content, not original work.

## 2. Triggering (25%) — the biggest lever
- **WHEN:** the description says when to fire (`Use this when…`). ~68% of the
  corpus does this.
- **Anti-trigger:** it says when NOT to fire (`Do NOT use when…`). **Only ~2.5%**
  of the corpus does — the single rarest and cheapest win. Always add it.
- The two together let the model route correctly and avoid false fires.

## 3. Disclosure (15%)
- Long reference material lives in sibling files (`reference/`, `scripts/`,
  `assets/`) that the body links to, instead of bloating `SKILL.md`.
- Body over ~2,200 words with no reference files = poor disclosure.
- ~50% of the corpus uses reference files; canonical repos ~43%+ and rising.

## 4. Structure (15%)
- Standard headings; a stated **Output** format where format matters (67% of even
  Anthropic's own skills leave output format unstated — a real gap).
- One job per skill. Near-identical overlapping skills should be merged.

## 5. Safety (25%) — the axis most skills skip

### allowed-tools scoping
- 16% of the corpus declares `allowed-tools`. It's a real scoping/safety control.
- **Declare it when the skill takes actions; omit it when it only produces
  content** (capability skills like document/art generation need broad access).
- **Scope dangerous tools.** Of all `Bash` grants in the corpus, **>50% are bare
  `Bash`** (full shell) vs scoped `Bash(git*)`. Bare shell defeats the purpose —
  recommend the narrowest pattern that still works.
- Top declared tools: Bash, Read, Grep, Write, Glob, Edit. Grant the minimum.

### Regulated / sensitive data
- **376 of ~5,000 skills** touch HIPAA / PHI / PII / GDPR / SSN / patient /
  medical data; **only 48%** of those mention *any* safeguard.
- If the skill touches such data, a **Data handling** section is **required**:
  - what data it reads/writes,
  - redaction / de-identification before processing,
  - never log or echo sensitive values,
  - retention, consent, and locale (GDPR/HIPAA) where relevant.
- Credentials/secrets count: never instruct the skill to print or commit tokens.

### High-stakes actions
- ~50% of the corpus mentions deploy / delete / drop / migrate / production /
  payments. Any irreversible or costly action needs a **dry-run, explicit
  confirmation, or validation** step before it runs. Our auditor flags
  `high-stakes-no-safety` when these appear with no guard.

## Grade bands
A ≥ 85 · B ≥ 70 · C ≥ 55 · D ≥ 40 · F < 40. "Best practice" = A on quality **and**
no open safety/data blocker.
