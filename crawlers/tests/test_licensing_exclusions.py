"""Tests for the licence allow-list, excerpt caps and the removal list."""
import json

import pytest

from crawlers import exclusions, licensing


def skill(lic=None, body="Body text."):
    fm = "name: demo\ndescription: Demo skill."
    if lic is not None:
        fm += f"\nlicense: {lic}"
    return f"---\n{fm}\n---\n\n{body}\n"


@pytest.mark.parametrize("raw,spdx", [
    ("MIT", "MIT"), ('"MIT"', "MIT"), ("mit", "MIT"), ("Apache-2.0", "Apache-2.0"),
    ("Apache License 2.0", "Apache-2.0"), ("BSD-3-Clause", "BSD-3-Clause"),
    ("CC BY 4.0", "CC-BY-4.0"), ("CC0-1.0", "CC0-1.0"),
])
def test_allowed_licences_normalise(raw, spdx):
    assert licensing.normalise(raw) == spdx


@pytest.mark.parametrize("raw", [
    "Proprietary. LICENSE.txt has complete terms",
    "Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)",
    "MIT + Commons Clause", "CC-BY-NC-SA-4.0", "GPL-3.0", "Complete terms in LICENSE.txt",
    "", None,
])
def test_other_licences_are_not_allowed(raw):
    assert licensing.normalise(raw) is None


def test_skill_licence_overrides_permissive_repo():
    assert licensing.permits_full_text("MIT", skill())
    assert licensing.permits_full_text("MIT", skill("Apache-2.0"))
    assert not licensing.permits_full_text("MIT", skill("Proprietary"))
    assert not licensing.permits_full_text("MIT", skill("MIT + Commons Clause"))
    assert not licensing.permits_full_text(None, skill("MIT"))
    assert not licensing.permits_full_text("GPL-3.0", skill())


def test_must_remove_is_narrower_than_not_allowed():
    assert licensing.must_remove("Proprietary. LICENSE.txt has complete terms")
    assert licensing.must_remove("CC BY-NC 4.0")
    assert not licensing.must_remove("MIT + Commons Clause")
    assert not licensing.must_remove("MIT")


def test_excerpt_caps():
    long = "x" * 1000
    kept = licensing.cap_excerpts([long, long, long, long])
    assert all(len(e) <= licensing.EXCERPT_MAX_CHARS for e in kept)
    assert sum(map(len, kept)) <= licensing.EXCERPT_CHARS_PER_FILE_MAX
    assert len(licensing.cap_excerpts(["a"] * 10)) == licensing.EXCERPTS_PER_FILE_MAX


def test_git_blob_sha_matches_git():
    # `printf 'hello\n' | git hash-object --stdin`
    assert exclusions.git_blob_sha("hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_scrub_removes_by_content_in_every_repo():
    bad = skill("Proprietary")
    ex = exclusions.Exclusions(repos={"Opted/Out"}, blobs={exclusions.git_blob_sha(bad)})
    rows = [
        {"repo_full_name": "a/one", "file_sha": exclusions.git_blob_sha(bad), "skill_md_content": bad},
        {"repo_full_name": "b/copy", "file_sha": "0" * 40, "skill_md_content": bad},  # stale sha
        {"repo_full_name": "opted/out", "file_sha": "1" * 40, "skill_md_content": skill()},
        {"repo_full_name": "c/fine", "file_sha": "2" * 40, "skill_md_content": skill("MIT")},
    ]
    assert exclusions.scrub_rows(rows, ex) == 3
    assert [r["skill_md_content"] is None for r in rows] == [True, True, True, False]
    assert rows[2]["content_removed"] == "repo-excluded"
    assert rows[0]["content_removed"] == "blob-excluded"
    assert rows[0]["file_sha"]  # pointer kept


def test_load_rejects_bad_sha_and_missing_file(tmp_path):
    p = tmp_path / "ex.json"
    p.write_text(json.dumps({"repos": [], "blobs": [{"sha": "abc"}]}))
    with pytest.raises(ValueError):
        exclusions.load(p)
    with pytest.raises(FileNotFoundError):
        exclusions.load(tmp_path / "missing.json")


def test_snapshots_hold_no_excluded_text():
    counts = exclusions.apply(exclusions.load(), write=False)
    assert sum(counts.values()) == 0, counts
