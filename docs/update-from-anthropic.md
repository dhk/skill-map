# If You're Using These Anthropic Skills, Update From Here

Anthropic's `skills` repo is the gold standard this whole study is calibrated
against — and most of it earns that (`mcp-builder` 95.5, `pdf` 93, `skill-creator`
93, all A-grade). But a handful of its skills don't follow **Anthropic's own
published guidance** (the `skill-creator` skill says a description should state
*what it does and when to use it*). This page names those specific skills, shows
the exact gap, and tells you where to go instead — either a higher-scoring
community alternative for the same job, or the one-line fix to apply in place.

Scores are from the v2 rubric (`crawlers/skill_quality.py`); reproduce with
`python crawlers/audit_repo.py --github anthropics/skills`.

> **Fairness note.** These are otherwise-good skills with a specific, small gap —
> usually a missing trigger line. This is not a teardown; it's a targeted upgrade
> list. And note the document skills (`docx`/`pdf`/`pptx`/`xlsx`) are
> *source-available, not open source* — read, don't fork.

---

## The skills that fall short, and what to do

| Anthropic skill | Score | The gap (vs Anthropic's own rubric) | Update from here |
|---|---|---|---|
| `webapp-testing` | 77 B | Description states *what* ("Toolkit for … testing local web applications using Playwright") but never *when* to invoke it | **Switch:** `julianobarbosa/claude-code-skills/playwright` (90 A) — same browser-testing job, states its trigger |
| `theme-factory` | 72 B | No WHEN-trigger and no anti-trigger; reads as a feature blurb, not an invocation cue | **Fix in place** (no better copy exists — the mega-collections cloned it verbatim at 72) |
| `doc-coauthoring` | 75 B | Good trigger, but the entire multi-step workflow is dumped inline — no progressive disclosure | **Fix in place:** move the workflow steps to `reference/workflow.md` and link |
| `frontend-design` | 75 B | No anti-trigger; doesn't say when *not* to fire (e.g. backend/API work) | **Fix in place** (community copies score the same 76) |

The pattern: **for these skills the mega-collections just copied the flaw** —
`webapp-testing`, `theme-factory`, and `doc-coauthoring` all appear in davila7 /
BbgnsurfTech / QuestForTech at the *identical* score. Copying propagated the gap;
it didn't fix it. The only place a genuinely better version exists is browser
testing, where independent `playwright` skills (90 A) beat Anthropic's
`webapp-testing` (77 B) by stating their trigger.

---

## The exact fixes ("update from here" in place)

### `webapp-testing` → add the trigger (or switch to a playwright skill)
Current description:
> Toolkit for interacting with and testing local web applications using
> Playwright. Supports verifying frontend functionality, debugging UI behavior,
> capturing browser screenshots, and viewing browser logs.

Upgraded:
> Toolkit for interacting with and testing local web applications using
> Playwright. **Use this when the user asks to test, debug, or screenshot a
> running local web app, verify frontend behavior, or inspect browser logs. Not
> for unit tests, CI config, or testing deployed/remote sites.**

### `theme-factory` → add when + when-not
> Toolkit for styling artifacts (slides, docs, reports, HTML pages) with one of 10
> preset themes or a generated theme. **Use this when the user asks to apply a
> visual theme, brand palette, or consistent styling to an already-created
> artifact. Not for generating the artifact's content itself.**

### `doc-coauthoring` → progressive disclosure
Keep the (good) description; move the inline 6-stage workflow into
`reference/coauthoring-workflow.md` and replace it in `SKILL.md` with a one-line
summary plus a link. This is the same fix the tuned LLM judge recommended for
`xlsx`.

### Every Anthropic skill → add an anti-trigger
**16 of 18** Anthropic skills lack a "when NOT to use" clause — the single rarest
practice in the entire ecosystem (2.5% corpus-wide). Even `mcp-builder` and
`pdf` skip it. Adding one sentence ("Not for …") measurably reduces
false-positive retrieval on adjacent tasks. `xlsx` is the model: *"not for Word
docs, Google Sheets, or standalone scripts."*

---

## What this is and isn't

- **Is:** a short, specific upgrade list where Anthropic's skills miss Anthropic's
  own rubric, with concrete diffs.
- **Isn't:** a claim that the alternatives are better *skills* wholesale — only
  that, for the named job, they score higher on definition quality. Test before
  adopting.
- **The meta-point:** copying a skill copies its flaws. If you pulled any of these
  from a mega-collection, you inherited the gap. Audit what you import:
  `python crawlers/audit_repo.py ~/.claude/skills`.
