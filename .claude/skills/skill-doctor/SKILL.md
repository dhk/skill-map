---
name: skill-doctor
description: >-
  Review an existing Claude Agent Skill and bring it up to best-practice
  standard. Use this when you have a SKILL.md to audit, harden, or improve — it
  interviews about allowed-tools scoping, data sensitivity (PHI/PII/HIPAA),
  high-stakes actions, triggering, and install scope, then recommends fixes and
  applies them on your confirmation. Do NOT use this to write a brand-new skill
  from scratch (use skill-creator) or to grade a whole repo at once (use the
  skill-map auditor / skill-audit Action).
license: MIT
---

# skill-doctor

Diagnose one Agent Skill against the gold standard and prescribe fixes.
Self-contained: the rubric is carried here as prose, so it runs anywhere with no
extra tooling. It **recommends first, then edits the file in place only after you
confirm.**

The rubric and the ecosystem evidence behind each check live in
[`reference/rubric.md`](reference/rubric.md). Read it when you need the detailed
scoring or the corpus numbers; the workflow below is enough for a normal review.

## When to use
- You have a `SKILL.md` and want it audited or hardened.
- Someone asks "is this skill any good?" or "make this best practice."

## When NOT to use
- Authoring a skill from a blank page → use `skill-creator`.
- Grading an entire repo of skills at once → use the skill-map auditor
  (`audit_repo.py`) or the `skill-audit` GitHub Action.

## Workflow

Follow these steps in order. Do not skip the interview — the highest-value fixes
(tool scoping, data handling, anti-triggers) cannot be inferred from the file
alone.

### 1. Read the skill
Read the target `SKILL.md` and its sibling files (`reference/`, `scripts/`,
`assets/`). Note: frontmatter keys present, description length, whether the body
has a WHEN trigger and an anti-trigger, headings, and any sibling files.

### 2. Static pass (no questions yet)
Score it silently against the checklist in `reference/rubric.md`:
frontmatter · triggering · disclosure · structure · **safety**. Write down the
concrete gaps. Detect signals you'll confirm in the interview:
- **Tool actions** — does the body run shell/network/file-mutation? (→ allowed-tools)
- **Regulated data** — does it mention health/PHI/PII/HIPAA/GDPR/SSN/patient,
  payments, or credentials/secrets? (→ data-handling section)
- **High-stakes ops** — deploy, delete, drop/migrate, production, force-push,
  payments? (→ safety scaffolding)

### 3. Interview (use AskUserQuestion)
Ask only the questions the static pass made relevant — never the whole bank.
Batch related questions into a single AskUserQuestion call (2–4 at a time).
The full wording and options are in
[`reference/interview-bank.md`](reference/interview-bank.md). The dimensions:

1. **allowed-tools** — which tools does this skill legitimately need? If it runs
   shell, push to **scope** it: `Bash(git*)`, not bare `Bash`. (In the crawled
   corpus, >50% of `Bash` grants are unscoped — the most common real gap.)
2. **Data sensitivity / PHI** — does it touch regulated or sensitive data? If
   **yes**, a data-handling section is **required** before this skill can be
   called best-practice (see §5). Half of regulated-data skills in the corpus
   ship with no safeguard at all.
3. **High-stakes surface** — does it take irreversible/costly actions? If so,
   require a dry-run / confirmation / validation step.
4. **Triggering** — when SHOULD it fire, and when should it NOT? ~97% of skills
   omit the anti-trigger; add `Do NOT use when…` to the description.
5. **Scope & install** — repo-local or global? (see §6, including symlinks).

### 4. Present the diagnosis
Give a short, prioritized report: **Critical** (safety/data) → **Should**
(triggering, tool scoping) → **Polish** (frontmatter, structure). For each, show
the exact before→after edit you propose. Be specific, not generic.

### 5. Apply on confirmation
For each proposed edit, get an OK, then make it with the Edit tool. Apply
mechanical fixes (frontmatter keys, anti-trigger clause, headings) eagerly once
confirmed; discuss judgment calls (scope, tool list) before editing.

**Regulated-data gate:** if §3.2 confirmed PHI/PII/HIPAA/financial data, do NOT
declare the skill best-practice until it has an explicit **Data handling**
section covering: what data it touches, redaction/de-identification, no-logging
of sensitive values, and retention/consent where relevant. Offer to draft it.

### 6. Scope and symlinking
Recommend an install scope and say why:
- **Repo-local** (`.claude/skills/<name>/` in the project) — when the skill
  encodes project-specific conventions, paths, or data. Travels with the repo;
  shared with the team via version control.
- **Global / personal** (`~/.claude/skills/<name>/`) — when it's a
  general-purpose capability you want everywhere.

If a skill is useful both ways, recommend keeping **one source of truth** (in the
repo) and **symlinking** it into the personal dir rather than copying:

```bash
ln -s "$(pwd)/.claude/skills/<name>" ~/.claude/skills/<name>
```

Only suggest a symlink when it genuinely avoids drift (the same skill wanted in
two locations). Don't symlink project-specific skills into the global dir — that
leaks project context everywhere. Note for the user that symlinks don't survive
some sync tools and aren't portable to Windows without dev-mode.

## Output
End with: the prioritized fix list, which fixes were applied, any that need the
author's judgment, and the recommended install scope. If a data-handling section
was required and not yet written, flag it as the one remaining blocker.
