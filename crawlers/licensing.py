"""
licensing.py — Decide whether a SKILL.md text may be republished in full.

DATA-POLICY.md rule 4: full text goes into a published dataset only when both
the repository's licence and the skill's own declared licence (its frontmatter
`license:` field, if it has one) are on the allow-list below. Anything else is
published as a pointer (repository, path, blob SHA) and derived values only.

Rule 3: evidence excerpts are short, and each source file has a total cap.

Standard library only.
"""
from __future__ import annotations

import re

# SPDX identifiers whose terms allow redistribution of the text with notice.
ALLOWED = frozenset({
    "MIT", "MIT-0",
    "Apache-2.0",
    "BSD-2-Clause", "BSD-3-Clause", "0BSD",
    "CC-BY-4.0", "CC-BY-3.0",
    "CC0-1.0",
})

# Excerpt caps (DATA-POLICY.md rule 3).
EXCERPT_MAX_CHARS = 300          # one excerpt
EXCERPTS_PER_FILE_MAX = 3        # excerpts quoted from one source file
EXCERPT_CHARS_PER_FILE_MAX = 600 # all excerpts from one source file together

# Free-text licence strings seen in SKILL.md frontmatter and repo metadata,
# mapped to SPDX. Matching is on a normalised form (lowercase, no punctuation).
_ALIASES = {
    "mit": "MIT",
    "mit license": "MIT",
    "the mit license": "MIT",
    "mit0": "MIT-0",
    "apache20": "Apache-2.0",
    "apache 20": "Apache-2.0",
    "apache license 20": "Apache-2.0",
    "apache license version 20": "Apache-2.0",
    "apache2": "Apache-2.0",
    "bsd2clause": "BSD-2-Clause",
    "bsd 2clause": "BSD-2-Clause",
    "bsd3clause": "BSD-3-Clause",
    "bsd 3clause": "BSD-3-Clause",
    "0bsd": "0BSD",
    "ccby40": "CC-BY-4.0",
    "cc by 40": "CC-BY-4.0",
    "creative commons attribution 40": "CC-BY-4.0",
    "creative commons attribution 40 international": "CC-BY-4.0",
    "ccby30": "CC-BY-3.0",
    "cc by 30": "CC-BY-3.0",
    "cc010": "CC0-1.0",
    "cc0 10": "CC0-1.0",
    "cc0": "CC0-1.0",
}

# Words that disqualify a licence string outright, whatever else it says.
_RESTRICTIVE = re.compile(
    r"propriet|non-?commercial|\bnc\b|commons clause|all rights reserved|"
    r"no derivatives|\bnd\b|confidential",
    re.I,
)


def normalise(raw: str | None) -> str | None:
    """Map a free-text or SPDX licence string to an SPDX id, or None if unknown."""
    if raw is None:
        return None
    text = str(raw).strip().strip("\"'").strip()
    if not text:
        return None
    if _RESTRICTIVE.search(text):
        return None
    for spdx in ALLOWED:
        if text.lower() == spdx.lower():
            return spdx
    key = re.sub(r"[^a-z0-9 ]", "", text.lower().replace("-", " ")).strip()
    key = re.sub(r"\s+", " ", key)
    return _ALIASES.get(key) or _ALIASES.get(key.replace(" ", ""))


def is_restrictive(raw: str | None) -> bool:
    """True when a licence string carries any term that keeps it off the
    allow-list (proprietary, non-commercial, Commons Clause, no derivatives)."""
    return bool(raw) and bool(_RESTRICTIVE.search(str(raw)))


# Narrower: texts already in the snapshots whose own licence says proprietary
# or non-commercial are removed from the snapshots (DATA-POLICY.md). Other
# restrictive terms only keep a text out of new published datasets.
_REMOVE = re.compile(r"propriet|non-?commercial|\bnc\b|all rights reserved", re.I)


def must_remove(raw: str | None) -> bool:
    """True when a declared licence says proprietary or non-commercial."""
    return bool(raw) and bool(_REMOVE.search(str(raw)))


_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---", re.S)
_LICENSE_LINE = re.compile(r"^license:\s*(.*)$", re.M | re.I)


def skill_license(text: str | None) -> str | None:
    """The raw `license:` value from a SKILL.md frontmatter, if declared."""
    if not text:
        return None
    m = _FRONTMATTER.match(text)
    if not m:
        return None
    lic = _LICENSE_LINE.search(m.group(1))
    if not lic:
        return None
    value = lic.group(1).strip()
    return value or None


def permits_full_text(repo_license: str | None, skill_text: str | None) -> bool:
    """Rule 4: may this text be republished in full?

    The repository licence must be on the allow-list. If the skill declares its
    own licence, that must be on the allow-list too, because a skill can carry
    stricter terms than the repository around it.
    """
    if normalise(repo_license) is None:
        return False
    declared = skill_license(skill_text)
    if declared is None:
        return True
    return normalise(declared) is not None


def cap_excerpts(excerpts: list[str]) -> list[str]:
    """Apply rule 3's caps: trim each excerpt, then keep excerpts in order
    until the per-file count or character budget runs out."""
    kept: list[str] = []
    used = 0
    for ex in excerpts:
        if len(kept) >= EXCERPTS_PER_FILE_MAX:
            break
        ex = ex[:EXCERPT_MAX_CHARS]
        if used + len(ex) > EXCERPT_CHARS_PER_FILE_MAX:
            ex = ex[: EXCERPT_CHARS_PER_FILE_MAX - used]
        if not ex:
            break
        kept.append(ex)
        used += len(ex)
    return kept
