# Just Add These Skills — the general-purpose set

Some skills show up across many independent repos *and* are consistently
well-built. Those are the closest thing the ecosystem has to a **standard
library**: if you don't have them, you probably should.

**Definition:** a concept counts as general-purpose if it appears in **≥ 4
distinct repos** with a **median quality ≥ 75** across the corpus. 63 concepts
qualify. The top of the list:

| Skill concept | Adopted by N repos | Median quality |
|---|---|---|
| skill-creator | 9 | 91.0 |
| pdf | 7 | 83.8 |
| code-reviewer | 6 | 84.8 |
| brand-guidelines | 6 | 80.0 |
| handoff | 6 | 78.2 |
| playwright | 5 | 88.0 |
| seo-audit | 5 | 87.5 |
| docx | 5 | 85.0 |
| changelog-generator | 5 | 85.0 |
| programmatic-seo | 5 | 84.5 |
| deep-research | 5 | 83.8 |
| internal-comms | 5 | 82.5 |
| xlsx | 5 | 77.0 |
| mcp-builder | 4 | 95.5 |
| senior-data-engineer | 4 | 89.0 |
| product-manager-toolkit | 4 | 89.0 |

(Full ranked list: `python -c "import json,sys; sys.path.insert(0,'crawlers'); from audit_repo import general_purpose_index; ..."` — or just run the auditor, which prints the ones *you* are missing.)

## Two clusters worth calling out

**1. The "document I/O" core** — `pdf`, `docx`, `xlsx`, `pptx`. These come
straight from Anthropic's own repo and are the most-copied skills in the
ecosystem. Nearly every serious collection has them. If you process files, add
them rather than reinventing them.

**2. The "meta" skills** — `skill-creator` (9 repos, median 91) and
`mcp-builder` (4 repos, 95.5). The most widely-copied, highest-quality
skills are the ones that *help you build more skills*. That's a strong signal:
**adopt `skill-creator` first** — it bakes the gold standard into everything you
write next.

## "Update your skills to include these practices"

Beyond adding whole skills, these are the practice-level changes that generalize
to *every* skill you already have (in priority order, from the corpus defect
data):

1. **Add a WHEN-trigger to every description.** ~31% of the corpus still lacks one. The
   single highest-leverage edit. Pattern: *"<What it does>. Use this when <the
   user does / asks for X>."*
2. **Expand thin descriptions** to two clauses (what + when). 8% are under 8
   words (most apparent-thinness was a parser artifact, now fixed).
3. **Normalize frontmatter** to `name` / `description` / `license`. Drop bespoke
   keys; lowercase-hyphenate names; match `name` to the directory.
4. **Use progressive disclosure.** If a body runs long, move depth into
   `reference.md` / scripts and link to them.
5. **Add a `skill-creator` skill and a CI gate** (`skill_quality.py`) so new
   skills inherit all of the above automatically.

## How to apply this to your repo

```bash
python crawlers/audit_repo.py ~/.claude/skills
# → prints YOUR signature, YOUR worst offenders, and the
#   general-purpose skills YOU are missing, ranked by adoption.
```
