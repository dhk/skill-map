# Repo Signature Playbook — "If your repo looks like this, do that"

Every skills repo has a **signature** — a coarse archetype computed from
observable features (skill count, ownership, quality median + variance). The
signature is computed the same way for the crawled corpus and for your own
private repo, so the benchmarks below apply directly to you.

Find your signature, read your row, run the auditor:

```bash
python crawlers/audit_repo.py ~/.claude/skills          # local
python crawlers/audit_repo.py --github you/your-repo    # GitHub (public or private + --token)
```

How signatures are assigned (by scale, then refined):

| Signature | Rule of thumb |
|---|---|
| `canonical-reference` | official-org, small & curated, high + consistent quality |
| `mega-collection` | ≥ 250 skills |
| `marketplace` | 60–249 skills |
| `domain-pack` | 15–59 skills, usually one subject area |
| `boutique` | 5–14 skills |
| `single-skill` | < 5 skills |

---

## mega-collection — *the highest-impact fixes in the ecosystem*

> 5 repos · 3,775 skills · **median 80.0** · **64%** have WHEN-triggers

You hold 77% of the ecosystem's skills and set its median. Coverage is not your
problem — **consistency is**. A third of your skills can't tell Claude when to
fire.

**Do this:**
1. **Add a CI quality gate.** Run `crawlers/skill_quality.py` on every PR; reject
   anything below grade C. This one change would move the ecosystem median by
   double digits.
2. **Backfill WHEN-triggers.** ~36% of your skills still lack one. Sweep
   descriptions to the "Use this when…" pattern.
3. **Deduplicate.** Collections this size accrete near-identical skills; merge them.
4. **Normalize frontmatter** to `name` / `description` / `license`.

**Top skills your peers have that you may be missing:** `ceo-advisor`,
`cto-advisor`, `code-reviewer`, `senior-architect`, `senior-backend`,
`computer-vision`.

---

## marketplace — *consistency across contributors*

> 6 repos · 594 skills · median 90.0 · 87% have WHEN-triggers

Multi-domain catalogs with many contributors. You're already good; the risk is
drift between authors.

**Do this:**
1. Publish a **shared frontmatter schema** and validate it on PR.
2. Keep naming conventions uniform; group by domain.
3. Trim stub skills (<40-word bodies) — they dilute the catalog.
4. Push depth into reference files (only 28% of you do — the lowest of the
   high-quality signatures).

**Top skills to add:** `skill-creator`, `code-reviewer`, `deep-research`,
`git-worktree-manager`.

---

## domain-pack — *depth over breadth*

> 12 repos · 410 skills · median 85.0 · 73% have WHEN-triggers · **58% use refs (best in class)**

Focused on one subject. You already lead on progressive disclosure. Polish the
descriptions and you're at the canonical bar.

**Do this:**
1. Make descriptions trigger **precisely within the domain** (you're at 81%; the
   canonical repos are at 87%).
2. Cross-link related skills.
3. Match `name` to directory; keep slugs consistent.

**Top skills to add (domain-adjacent, high adoption):** `seo-audit`,
`programmatic-seo`, `handoff`, `code-review`.

---

## boutique — *small enough to make every skill an A*

> 6 repos · 49 skills · median 82.5 · 87% have WHEN-triggers

A handful of personal skills. At this size there's no excuse not to be all-A.

**Do this:**
1. Audit every skill against the rubric and fix individually — aim for all-A.
2. Add the WHEN-trigger pattern to every description.
3. Add headings + a concrete example to thin bodies.

> ⚠️ The LLM deep-read was harsher on boutique repos than the structural score —
> several skills that score well structurally read as "weak" on substance. At
> this size, do the qualitative read too.

---

## single-skill — *make the one skill exemplary*

> 7 repos · 7 skills · median 85.0

Often a skill embedded in a larger product/docs repo. It's your showcase.

**Do this:**
1. Full frontmatter, a razor-sharp trigger, one concrete example.
2. If it's growing, split into multiple skills **before** it becomes a dump.

---

## canonical-reference — *you are the bar*

> 5 repos · 118 skills · median 90.0 · 87% have WHEN-triggers

Official, curated, consistent. Keep it that way.

**Do this:**
1. Keep the set tight — every skill earns its place.
2. Maintain a `SKILL.md` template and lint new skills against it.
3. Even here, 13% lack a WHEN-trigger and nearly all lack an anti-trigger — close the gap; everyone copies you.

---

## How "top skills to add" is computed

A concept counts as **general-purpose** if it appears in **≥ 4 repos** with a
**median quality ≥ 75** across the corpus — i.e. widely adopted *and* well-built.
The auditor recommends the general-purpose concepts your repo lacks, ranked by
adoption. See [just-add-these-skills.md](just-add-these-skills.md) for the full
list, and run `audit_repo.py` for a recommendation tailored to your repo.
