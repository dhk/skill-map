# Interview bank

Question wording for the AskUserQuestion calls in step 3. Ask **only** what the
static pass flagged as relevant, and **batch** related questions into one call
(2–4 questions). Each question should offer a recommended option first.

## A. allowed-tools (ask when the body runs shell / network / file mutation)
- **Q: Which tools does this skill legitimately need?** Options drawn from the
  tools the body actually uses (Read, Write, Edit, Grep, Glob, Bash, WebFetch,
  Task, …). Recommend the minimum set.
- **Q (if Bash needed): How should Bash be scoped?** Options:
  - `Bash(<pattern>*)` — scope to the commands it runs (recommended; e.g.
    `Bash(git*)`, `Bash(npm*)`).
  - Bare `Bash` — full shell (only if it genuinely needs arbitrary commands).
- **Q: Is this a capability skill (produces content) or an action skill (does
  things)?** Capability → omit `allowed-tools`. Action → declare it.

## B. Data sensitivity / PHI (ask when regulated/sensitive terms appear)
- **Q: Does this skill read or write regulated or sensitive data?** Options:
  - PHI / health (HIPAA), PII (names/SSN/contact), Financial/payments,
    Credentials/secrets, None of these.
  (multiSelect.)
- **Q (if any selected): What safeguards are in place / wanted?** Options:
  redact-or-de-identify before processing · never log sensitive values ·
  retention & consent handling · all of these (recommended).
  → If regulated data is confirmed, a **Data handling** section is REQUIRED
  before the verdict (see rubric §5).

## C. High-stakes surface (ask when deploy/delete/prod/payment terms appear)
- **Q: Does this skill take irreversible or costly actions?** Options:
  Yes — needs a guard · No — read-only/reversible.
- **Q (if yes): Which guard fits?** dry-run/preview first · explicit
  confirmation prompt · validation/checks before acting · all of these.

## D. Triggering (almost always ask)
- **Q: When should this skill fire — and when should it explicitly NOT?**
  Capture both; the anti-trigger goes into the description as `Do NOT use when…`.

## E. Scope & install (always ask)
- **Q: Where should this skill live?** Options:
  - Repo-local (`.claude/skills/`) — project-specific; travels with the repo
    (recommended for skills encoding project conventions).
  - Global (`~/.claude/skills/`) — general-purpose; available everywhere.
  - Both — keep one source of truth and **symlink** (see SKILL.md §6).
- **Q (if Both): Symlink from repo into the personal dir?** Yes (recommended —
  avoids drift) · No, maintain copies. Warn: symlinks may not survive some sync
  tools and need dev-mode on Windows.
