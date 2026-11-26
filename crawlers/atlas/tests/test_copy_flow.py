"""Tests for the copy-flow export (crawlers/atlas/copy_flow.py)."""
from __future__ import annotations

import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from crawlers.atlas import copy_flow as cf
from crawlers.exclusions import Exclusions

A, B, C = "a" * 40, "b" * 40, "c" * 40

VERSIONS = [
    {"vendor": "Acme", "repo": "acme/skills", "path": "s/alpha/SKILL.md", "blob_sha": A, "removal_listed": False},
    {"vendor": "Acme", "repo": "acme/skills", "path": "s/alpha/SKILL.md", "blob_sha": B, "removal_listed": False},
    {"vendor": "Acme", "repo": "acme/skills", "path": "s/secret/SKILL.md", "blob_sha": C, "removal_listed": True},
    {"vendor": "Globex", "repo": "globex/p", "path": "beta/SKILL.md", "blob_sha": "d" * 40, "removal_listed": False},
]
SKILLS = [
    {"vendor": "Acme", "repo": "acme/skills", "path": "s/alpha/SKILL.md", "authorship": "first-party",
     "manifest_author": "Acme", "versions": 2, "first_landed_at": "2026-01-01T00:00:00Z", "present_at_head": True},
    {"vendor": "Acme", "repo": "acme/skills", "path": "s/secret/SKILL.md", "authorship": "unstated",
     "manifest_author": None, "versions": 1, "first_landed_at": "2026-02-01T00:00:00Z", "present_at_head": True},
    {"vendor": "Globex", "repo": "globex/p", "path": "beta/SKILL.md", "authorship": "unstated",
     "manifest_author": None, "versions": 1, "first_landed_at": "2026-03-01T00:00:00Z", "present_at_head": False},
]


def m(sha, path, repo, copy_path, folder):
    return {"blob_sha": sha, "vendor": "Acme", "vendor_repo": "acme/skills", "vendor_path": path,
            "vendor_first_landed_at": "2026-01-01T00:00:00Z", "copy_repo": repo,
            "copy_path": copy_path, "copy_platform_folder": folder}


MIRROR = [
    m(A, "s/alpha/SKILL.md", "u/one", ".claude/skills/alpha/SKILL.md", "claude"),
    m(B, "s/alpha/SKILL.md", "u/one", ".agents/skills/alpha/SKILL.md", "agents"),
    m(A, "s/alpha/SKILL.md", "U/Two", ".claude/skills/alpha/SKILL.md", "claude"),
    m(A, "s/alpha/SKILL.md", "bad/fork", "SKILL.md", None),
    m(C, "s/secret/SKILL.md", "u/one", "x/SKILL.md", "weird"),
]
CROSS = [{"origin_vendor": "Acme", "origin_repo": "acme/skills", "origin_path": "s/alpha/SKILL.md",
          "origin_landed_at": "2026-01-01T00:00:00Z", "copy_vendor": "Globex", "copy_repo": "globex/p",
          "copy_path": "alpha/SKILL.md", "copy_landed_at": "2026-02-01T00:00:00Z",
          "copy_authorship": "first-party", "same_day": False}]
EX = Exclusions({"bad/fork"}, set())


def built(**kw):
    return cf.build(VERSIONS, SKILLS, MIRROR, CROSS, EX, **kw)


def test_skills_aggregate_copies_repos_versions_and_platforms():
    d = built(min_skills=1)
    alpha = next(s for s in d["skills"] if s["name"] == "alpha")
    assert (alpha["copies"], alpha["copy_repos"], alpha["versions_copied"]) == (3, 2, 2)
    assert alpha["by_platform"] == {"claude": {"copies": 2, "repos": 2}, "agents": {"copies": 1, "repos": 1}}
    assert alpha["authorship"] == "first-party" and alpha["versions"] == 2
    secret = next(s for s in d["skills"] if s["name"] == "secret")
    assert secret["removal_listed"] and secret["by_platform"] == {"other": {"copies": 1, "repos": 1}}
    assert d["skills"][0]["name"] == "alpha"  # most copying repos first


def test_removal_list_drops_copy_repos():
    d = built(min_skills=1)
    assert d["totals"]["copies_dropped_removal_list"] == 1
    assert "bad/fork" not in {r["repo"] for r in d["repos"]}
    assert d["totals"]["copies"] == 4


def test_vendor_rows_include_vendors_with_no_copies():
    v = {r["vendor"]: r for r in built()["vendors"]}
    assert v["Acme"] == {"vendor": "Acme", "skills_published": 2, "skills_copied": 2,
                         "copies": 4, "copy_repos": 2}
    assert v["Globex"]["skills_copied"] == 0


def test_repos_and_edges_respect_min_skills_and_cap():
    d = built(min_skills=2)
    assert [r["repo"] for r in d["repos"]] == ["u/one"]
    assert {(e["skill"], e["copies"]) for e in d["edges"]} == {
        ("acme/skills:s/alpha/SKILL.md", 2), ("acme/skills:s/secret/SKILL.md", 1)}
    assert built(min_skills=1, max_repos=1)["totals"]["repos_shown"] == 1


def test_cross_vendor_passthrough():
    c = built()["cross_vendor"][0]
    assert c["origin_skill"] == "acme/skills:s/alpha/SKILL.md" and c["copy_vendor"] == "Globex"


def test_run_writes_pointer_only_json(tmp_path):
    for name, rows in (("version", VERSIONS), ("skill", SKILLS), ("mirror", MIRROR), ("cross_vendor", CROSS)):
        pq.write_table(pa.Table.from_pylist(rows), tmp_path / f"{name}.parquet")
    (tmp_path / "manifest.json").write_text(json.dumps(
        {"method_version": "vendor-reference/1.1.0", "mirror": {"gitskills_revision": "abc"}}))
    exc = tmp_path / "ex.json"
    exc.write_text(json.dumps({"repos": [{"repo": "bad/fork"}], "blobs": []}))
    out = tmp_path / "copy_flow.json"
    d = cf.run(tmp_path, out, exc, min_skills=1)
    saved = json.loads(out.read_text())
    assert saved["meta"]["gitskills_revision"] == "abc"
    assert saved["totals"] == d["totals"]
    assert "content" not in out.read_text() and "description" not in out.read_text()


def test_run_needs_mirror(tmp_path):
    with pytest.raises(FileNotFoundError):
        cf.run(tmp_path, tmp_path / "x.json")
