"""Tests for the copy-flow export (crawlers/atlas/copy_flow.py)."""
from __future__ import annotations

import hashlib
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


def m(sha, path, repo, copy_path, folder, credit="vendor", authorship="first-party", author="Acme"):
    return {"blob_sha": sha, "vendor": "Acme", "vendor_repo": "acme/skills", "vendor_path": path,
            "vendor_first_landed_at": "2026-01-01T00:00:00Z", "vendor_authorship": authorship,
            "vendor_manifest_author": author, "credit": credit, "copy_repo": repo,
            "copy_path": copy_path, "copy_platform_folder": folder}


MIRROR = [
    m(A, "s/alpha/SKILL.md", "u/one", ".claude/skills/alpha/SKILL.md", "claude"),
    m(B, "s/alpha/SKILL.md", "u/one", ".agents/skills/alpha/SKILL.md", "agents"),
    m(A, "s/alpha/SKILL.md", "U/Two", ".claude/skills/alpha/SKILL.md", "claude"),
    m(A, "s/alpha/SKILL.md", "bad/fork", "SKILL.md", None),
    m(C, "s/secret/SKILL.md", "u/one", "x/SKILL.md", "weird", authorship="unstated", author=None),
]
CROSS = [{"origin_vendor": "Acme", "origin_repo": "acme/skills", "origin_path": "s/alpha/SKILL.md",
          "origin_landed_at": "2026-01-01T00:00:00Z", "copy_vendor": "Globex", "copy_repo": "globex/p",
          "copy_path": "alpha/SKILL.md", "copy_landed_at": "2026-02-01T00:00:00Z",
          "copy_authorship": "first-party", "same_day": False}]
EX = Exclusions({"bad/fork"}, {C})


def built(**kw):
    return cf.build(VERSIONS, SKILLS, MIRROR, CROSS, EX, **kw)


def test_skills_aggregate_copies_repos_versions_and_platforms():
    d = built(min_skills=1)
    alpha = next(s for s in d["skills"] if s["name"] == "alpha")
    assert (alpha["copies"], alpha["copy_repos"], alpha["versions_copied"]) == (3, 2, 2)
    assert alpha["by_platform"] == {"claude": {"copies": 2, "repos": 2}, "agents": {"copies": 1, "repos": 1}}
    assert alpha["authorship"] == "first-party" and alpha["versions"] == 2
    secret = next(s for s in d["skills"] if s["name"] == "secret")
    assert secret["removal_listed_copies"] == 1 and secret["by_platform"] == {"other": {"copies": 1, "repos": 1}}
    assert d["skills"][0]["name"] == "alpha"  # most copying repos first


def test_removal_list_drops_copy_repos():
    d = built(min_skills=1)
    assert d["totals"]["copies_dropped_removal_list"] == 1
    assert "bad/fork" not in {r["repo"] for r in d["repos"]}
    assert d["totals"]["copies"] == 4


def test_removal_listed_texts_are_counted_per_copy():
    # Only the copy whose own text is listed counts, not every copy of a skill with a listed version.
    mirror = MIRROR + [m(C, "s/alpha/SKILL.md", "u/three", "alpha/SKILL.md", "claude")]
    d = cf.build(VERSIONS, SKILLS, mirror, CROSS, EX, min_skills=1)
    alpha = next(s for s in d["skills"] if s["name"] == "alpha")
    assert (alpha["copies"], alpha["removal_listed_copies"]) == (4, 1)
    assert d["totals"]["copies_of_removal_listed_texts"] == 2
    unlisted = cf.build(VERSIONS, SKILLS, MIRROR, CROSS, Exclusions({"bad/fork"}, set()), min_skills=1)
    assert all(s["removal_listed_copies"] == 0 for s in unlisted["skills"])


def test_vendor_rows_include_vendors_with_no_copies():
    v = {r["vendor"]: r for r in built()["vendors"]}
    assert v["Acme"] == {"vendor": "Acme", "skills_published": 2, "skills_copied": 2,
                         "copies": 4, "copy_repos": 2,
                         "by_credit": {"vendor": {"skills_copied": 2, "copies": 4, "copy_repos": 2},
                                       "repackaged": {"skills_copied": 0, "copies": 0, "copy_repos": 0}}}
    assert v["Globex"]["skills_copied"] == 0


def test_repos_and_edges_respect_min_skills_and_cap():
    d = built(min_skills=2)
    assert [r["repo"] for r in d["repos"]] == ["u/one"]
    ids = [s["id"] for s in d["skills"]]
    assert {(ids[si], d["repos"][ri]["repo"], n) for si, ri, n in d["edges"]} == {
        ("acme/skills:s/alpha/SKILL.md", "u/one", 2), ("acme/skills:s/secret/SKILL.md", "u/one", 1)}
    assert built(min_skills=1, max_repos=1)["totals"]["repos_shown"] == 1


def test_skills_beyond_the_cap_are_summed_per_vendor():
    d = built(min_skills=1, max_skills=1)
    assert [s["name"] for s in d["skills"]] == ["alpha"]
    assert d["skills_rest"] == [{"vendor": "Acme", "credit": "vendor", "skills": 1, "copies": 1, "removal_listed_copies": 1,
                                 "by_platform": {"other": {"copies": 1}}}]
    assert all(si == 0 for si, _, _ in d["edges"])  # edges only to skills shown
    assert d["totals"]["skills_copied"] == 2 and d["totals"]["skills_shown"] == 1


def test_repackaged_skills_are_split_out_and_rank_below_the_vendors_own():
    guest = "e" * 40
    skills = SKILLS + [{"vendor": "Globex", "repo": "globex/p", "path": "sp/SKILL.md",
                        "authorship": "other-author", "manifest_author": "Jesse Vincent", "versions": 1,
                        "first_landed_at": "2026-01-01T00:00:00Z", "present_at_head": True}]
    extra = [{**m(guest, "sp/SKILL.md", f"u/r{i}", "SKILL.md", "claude", credit="repackaged",
                  authorship="other-author", author="Jesse Vincent"),
              "vendor": "Globex", "vendor_repo": "globex/p"} for i in range(5)]
    d = cf.build(VERSIONS, skills, MIRROR + extra, CROSS, EX, min_skills=1, max_skills=1)
    sp = d["skills"][0]  # five repositories: shown first, flagged as repackaged
    assert (sp["name"], sp["credit"], sp["manifest_author"]) == ("sp", "repackaged", "Jesse Vincent")
    g = {r["vendor"]: r for r in d["vendors"]}["Globex"]
    assert g["by_credit"]["repackaged"] == {"skills_copied": 1, "copies": 5, "copy_repos": 5}
    assert g["by_credit"]["vendor"]["copies"] == 0
    assert [v["vendor"] for v in d["vendors"]] == ["Acme", "Globex"]  # ranked by own reach
    assert d["totals"]["copies_by_credit"] == {"vendor": 4, "repackaged": 5}
    assert {(r["vendor"], r["credit"]) for r in d["skills_rest"]} == {("Acme", "vendor")}
    assert all(r["repackaged_copies"] == (1 if r["repo"].startswith("u/r") else 0) for r in d["repos"])


def test_cross_vendor_passthrough():
    c = built()["cross_vendor"][0]
    assert c["origin_skill"] == "acme/skills:s/alpha/SKILL.md" and c["copy_vendor"] == "Globex"


def write_inputs(tmp_path, mirror_section=True, mirror=MIRROR, **override):
    outputs = []
    for name, rows in (("version", VERSIONS), ("skill", SKILLS), ("mirror", mirror), ("cross_vendor", CROSS)):
        path = tmp_path / f"{name}.parquet"
        pq.write_table(pa.Table.from_pylist(rows), path)
        outputs.append({"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    for o in outputs:
        o["sha256"] = override.get(o["path"], o["sha256"])
    (tmp_path / "manifest.json").write_text(json.dumps({
        "method_version": "vendor-reference/1.1.0",
        "mirror": {"gitskills_revision": "abc"} if mirror_section else None, "outputs": outputs}))
    exc = tmp_path / "ex.json"
    exc.write_text(json.dumps({"repos": [{"repo": "bad/fork"}], "blobs": []}))
    return exc


TOP_KEYS = {"vendors", "skills", "skills_rest", "repos", "edges", "cross_vendor", "totals", "meta"}
SKILL_KEYS = {"id", "vendor", "repo", "path", "name", "credit", "authorship", "manifest_author", "versions",
              "first_landed_at", "present_at_head", "removal_listed_copies", "copies",
              "versions_copied", "copy_repos", "by_platform"}


def test_run_writes_only_allowed_keys(tmp_path):
    exc = write_inputs(tmp_path)
    out = tmp_path / "copy_flow.json"
    d, written = cf.run(tmp_path, out, exc, min_skills=1)
    assert written == out
    saved = json.loads(out.read_text())
    assert set(saved) == TOP_KEYS
    assert all(set(s) == SKILL_KEYS for s in saved["skills"])
    assert all(set(r) == {"repo", "skills", "copies", "vendors", "repackaged_copies"}
               for r in saved["repos"])
    assert saved["meta"]["credit_rule"] == cf.CREDIT_RULE
    assert all(len(e) == 3 and all(isinstance(x, int) for x in e) for e in saved["edges"])
    assert all(set(c) == {"origin_vendor", "origin_skill", "origin_landed_at", "copy_vendor", "copy_repo",
                          "copy_path", "copy_landed_at", "copy_authorship", "same_day"}
               for c in saved["cross_vendor"])
    assert set(saved["meta"]["inputs_sha256"]) == set(cf.INPUTS) | {"manifest.json"}
    assert saved["meta"]["gitskills_revision"] == "abc"
    assert saved["totals"] == d["totals"]


def test_run_needs_mirror(tmp_path):
    with pytest.raises(FileNotFoundError):
        cf.run(tmp_path, tmp_path / "x.json")


def test_run_refuses_manifest_without_mirror(tmp_path):
    exc = write_inputs(tmp_path, mirror_section=False)
    with pytest.raises(cf.StaleInputError, match="no mirror section"):
        cf.run(tmp_path, tmp_path / "x.json", exc)


def test_run_refuses_stale_mirror(tmp_path):
    exc = write_inputs(tmp_path, **{"mirror.parquet": "0" * 64})
    with pytest.raises(cf.StaleInputError, match="mirror.parquet"):
        cf.run(tmp_path, tmp_path / "x.json", exc)
    assert cf.main(["--src", str(tmp_path), "--out", str(tmp_path / "x.json"),
                    "--exclusions", str(exc)]) == 2


def test_run_refuses_mirror_without_credit(tmp_path):
    old = [{k: v for k, v in r.items() if k not in ("credit", "vendor_authorship", "vendor_manifest_author")}
           for r in MIRROR]
    exc = write_inputs(tmp_path, mirror=old)
    with pytest.raises(cf.StaleInputError, match="credit"):
        cf.run(tmp_path, tmp_path / "x.json", exc)


def test_caps_step_down_to_fit(tmp_path, monkeypatch):
    exc = write_inputs(tmp_path)
    cf.run(tmp_path, tmp_path / "small.json", exc, min_skills=1, max_skills=1)
    small = (tmp_path / "small.json").stat().st_size
    monkeypatch.setattr(cf, "FIT_STEPS", ((500, 1),))
    d, written = cf.run(tmp_path, tmp_path / "fit.json", exc, min_skills=1, max_bytes=small + 50)
    assert written == tmp_path / "fit.json"
    assert d["meta"]["caps"] == {"max_repos": 500, "max_skills": 1, "reduced_to_fit": True}
    assert len(d["skills"]) == 1 and d["skills_rest"]


def test_oversized_output_goes_to_release_dir(tmp_path):
    exc = write_inputs(tmp_path)
    out = tmp_path / "copy_flow.json"
    _, written = cf.run(tmp_path, out, exc, min_skills=1, max_bytes=100)
    assert written == tmp_path / "release" / "copy_flow.json" and not out.exists()
