# The rubric (self-contained)

Derived from `anthropics/skills` and validated against a crawl of ~5,000
`SKILL.md` files across 40+ repos. Two passes: a **hard-requirements gate**
(§0 — Anthropic's own SKILL.md validator, binary, no partial credit), then
**five weighted axes** — the first four are quality, the fifth is safety. A
skill that scores well on 1–4 but fails 5 is **not** best-practice. A skill
that fails §0 fails outright, regardless of how it scores elsewhere.

Score each axis 0–100 once the gate passes, then weight: frontmatter 20 ·
triggering 25 · disclosure 15 · structure 15 · safety 25.

See [`consider-this.md`](consider-this.md) for open questions and
forward-looking ideas that haven't been folded into scoring yet.

## 0. Hard requirements (pass/fail gate — check first)

Sourced directly from Anthropic's own `skill-creator` packaging validator
(`scripts/quick_validate.py`). These are mechanical and binary — a skill
either meets them or its packaging is rejected outright. There's no judgment
call here; check these before scoring anything else.

- **Frontmatter keys** are limited to exactly: `name`, `description`,
  `license`, `allowed-tools`, `metadata`, `compatibility`. Anything else —
  **including `version`** — is an unexpected key and fails packaging. (A
  Claude Code *plugin's* separate `plugin.json` may carry its own `version`
  field; that's a different namespace and is fine.)
- **`name`**: kebab-case only (`^[a-z0-9-]+$`) — lowercase letters, digits,
  hyphens. No leading/trailing hyphen, no double hyphen. **Max 64
  characters.**
- **`description`**: **max 1024 characters** (a character limit, not a word
  count — see §1 for the separate stylistic range). Must not contain `<` or
  `>` — angle brackets are rejected outright.
- **`compatibility`** (if present): max 500 characters.

## 1. Frontmatter (20%)
- `name` present. Matching the skill's directory name is a strong convention
  in elite skills (99% do; only 64% of the rest — a reliable tell), but it is
  **not enforced** by Anthropic's validator. Treat a mismatch as a
  suggestion, not a failure.
- `description` present, two clauses: *what it does* + *when to use it*.
  **14–80 words is the typical/tidy range** seen in high-quality corpus
  skills — a style guideline, not a ceiling. See §2: Anthropic's own current
  guidance explicitly favors longer, more explicit descriptions in some
  cases, and the real hard limit is the 1024-character cap in §0.
- `license` is common in canonical repos.
- `compatibility` and `metadata` are both legitimate, officially recognized
  frontmatter keys most authors don't know about. Use `compatibility`
  (≤500 chars) to note required tools/dependencies — that's a different
  purpose from `allowed-tools`, which scopes *permitted actions*, not
  *requirements*.
- **Red flag:** `origin` / `source` provenance keys usually mark
  copied/aggregated content, not original work — and they're outside the §0
  allowed set regardless.

## 2. Triggering (25%) — the biggest lever
- **WHEN:** the description says when to fire (`Use this when…`). ~68% of the
  corpus does this.
- **Anti-trigger — recommend contextually, not universally.** Stating when
  NOT to fire (`Do NOT use when…`) earns its keep when there's a plausible
  overlap with another skill in the same install scope — two PDF-adjacent
  skills, two deploy skills, a general skill next to a narrower specialized
  one. For a skill with an unambiguous, narrow domain and no obvious neighbor
  to confuse it with, a missing anti-trigger is **not** itself a defect —
  don't flag it as one just because it's present in the file. (Only ~2.5% of
  the corpus has one; that may partly reflect that most skills genuinely
  don't need one, not that everyone's missing a critical safeguard. Real
  user feedback on this exact check: "I get a lot of `no-anti-trigger` …
  which doesn't really feel necessary — what am I missing?" The honest
  answer, most of the time: not much.)
- **This cuts against over-trimming the description, too.** Anthropic's own
  current `skill-creator` guidance explicitly tells authors to make
  descriptions "a little pushy" — enumerating every context that should
  trigger the skill — because *undertriggering* is the more common failure
  mode in practice. Don't let an anti-trigger recommendation, or the 80-word
  range in §1, cut against a description that's legitimately long because
  it's doing exactly that.

## 3. Disclosure (15%)
- Long reference material lives in sibling files (`reference/`, `scripts/`,
  `assets/`) that the body links to, instead of bloating `SKILL.md`.
- **Primary threshold: body under ~500 lines** — this is Anthropic's current
  stated guidance (add another hierarchy layer if approaching it). A
  corpus-derived "~2,200 words" figure has circulated as a rough cross-check,
  but line count is the number Anthropic's own docs actually specify — treat
  it as authoritative over the word count.
- ~50% of the corpus uses reference files; canonical repos ~43%+ and rising.

## 4. Structure (15%)
- Standard headings; a stated **Output** format **when the skill produces a
  structured deliverable** — a file, a populated template, code with an
  expected shape, data with a defined schema. For skills whose output is
  naturally freeform or conversational, an unstated output format is **not**
  a defect — don't flag `output-format-unstated` on every skill regardless of
  what it actually produces. (This is the other check real users have called
  out as noisy — same fix as the anti-trigger above: contextual, not blanket.)
- **Voice, per Anthropic's own authoring guidance:** `description` in third
  person ("This skill should be used when…", not "Use this skill when…");
  body in imperative/infinitive form ("To do X, do Y"), not second person
  ("You should do X"). A skill that reads like second-person prose, or whose
  description is first-person, or that skips the standard anatomy
  (frontmatter → body → optional `scripts/`/`references/`/`assets/`) is a
  signal it likely wasn't drafted through `skill-creator`. Worth a light
  "this doesn't look like it went through skill-creator — consider a pass"
  note — **not** a scoring penalty, since skill-doctor only reads the file
  and can't confirm the skill actually underperforms (see
  [`consider-this.md`](consider-this.md)).
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
A ≥ 85 · B ≥ 70 · C ≥ 55 · D ≥ 40 · F < 40. "Best practice" = A on quality
**and** no open safety/data blocker **and** no §0 gate failure.
