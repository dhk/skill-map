"""Tests for the vendor reference set (crawlers/atlas/vendor_reference.py)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from crawlers.atlas import vendor_reference as vr

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
}


def sh(repo: Path, *args: str, date: str | None = None) -> str:
    env = dict(ENV)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout


def write(repo: Path, rel: str, text: str) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def commit(repo: Path, msg: str, date: str) -> str:
    sh(repo, "add", "-A")
    sh(repo, "commit", "-q", "-m", msg, date=date)
    return sh(repo, "rev-parse", "HEAD").strip()


def blob(text: str) -> str:
    from crawlers.exclusions import git_blob_sha
    return git_blob_sha(text)


@pytest.fixture()
def vendor_repo(tmp_path: Path) -> dict:
    """A small vendor repository with a plugin, a partner path, a merge, an unmerged branch, a delete."""
    repo = tmp_path / "acme__skills"
    repo.mkdir()
    sh(repo, "init", "-q", "-b", "main")
    write(repo, "plugins/core/.claude-plugin/plugin.json", json.dumps({"author": {"name": "Acme Inc"}}))
    write(repo, "plugins/core/skills/alpha/SKILL.md", "alpha v1\n")
    write(repo, "plugins/guest/.codex-plugin/plugin.json", json.dumps({"author": "Globex"}))
    write(repo, "plugins/guest/skills/beta/SKILL.md", "beta v1\n")
    write(repo, "partner-built/gamma/SKILL.md", "gamma v1\n")
    write(repo, "SKILL.md", "root\n")
    write(repo, "plugins/core/skills/alpha/README.md", "not a skill\n")
    # A manifest that is a symlink to a shared .plugin/ folder, and a .cursor-plugin folder.
    write(repo, "plugins/linked/.plugin/plugin.json", json.dumps({"author": {"name": "Acme Inc"}}))
    (repo / "plugins/linked/.claude-plugin").mkdir(parents=True)
    os.symlink("../.plugin/plugin.json", repo / "plugins/linked/.claude-plugin/plugin.json")
    write(repo, "plugins/linked/skills/eps/SKILL.md", "eps\n")
    write(repo, "plugins/cur/.cursor-plugin/plugin.json", json.dumps({"author": "Initech"}))
    write(repo, "plugins/cur/skills/zeta/SKILL.md", "zeta\n")
    c1 = commit(repo, "first", "2026-01-01T00:00:00+00:00")

    # A change made on a branch and merged later: it lands when the merge does.
    sh(repo, "checkout", "-q", "-b", "feature")
    write(repo, "plugins/core/skills/alpha/SKILL.md", "alpha v2\n")
    commit(repo, "alpha v2 on a branch", "2026-02-01T00:00:00+00:00")
    sh(repo, "checkout", "-q", "main")
    write(repo, "templates/x/.claude-plugin/plugin.json", json.dumps({"author": "Your Name"}))
    write(repo, "templates/x/SKILL.md", "template\n")
    commit(repo, "template", "2026-02-15T00:00:00+00:00")
    sh(repo, "merge", "-q", "--no-ff", "feature", "-m", "merge feature", date="2026-03-01T00:00:00+00:00")
    merge = sh(repo, "rev-parse", "HEAD").strip()

    # Never merged: must not appear.
    sh(repo, "checkout", "-q", "-b", "unmerged")
    write(repo, "plugins/core/skills/delta/SKILL.md", "delta\n")
    commit(repo, "unmerged", "2026-03-15T00:00:00+00:00")
    sh(repo, "checkout", "-q", "main")

    # Rename and delete.
    sh(repo, "mv", "partner-built/gamma", "partner-built/gamma2")
    commit(repo, "rename gamma", "2026-04-01T00:00:00+00:00")
    sh(repo, "rm", "-q", "plugins/guest/skills/beta/SKILL.md")
    last = commit(repo, "delete beta", "2026-05-01T00:00:00+00:00")
    return {"dir": repo, "first": c1, "merge": merge, "last": last}


CFG = {"vendor": "Acme", "names": ["Acme"], "repo": "acme/skills",
       "license": "MIT", "partner_paths": ["partner-built/"]}


def changes(vendor_repo):
    rows = vr.skill_changes(vendor_repo["dir"])
    vr.attach_authorship(rows, vendor_repo["dir"], CFG["names"], CFG["partner_paths"])
    return rows


# ---------------------------------------------------------------- history

def test_only_skill_files_on_the_default_branch(vendor_repo):
    paths = {r["path"] for r in changes(vendor_repo)}
    assert "plugins/core/skills/delta/SKILL.md" not in paths  # unmerged branch
    assert not any(p.endswith("README.md") for p in paths)
    assert "SKILL.md" in paths  # a root-level skill counts


def test_merged_change_is_dated_by_the_merge(vendor_repo):
    alpha = [r for r in changes(vendor_repo) if r["path"].endswith("alpha/SKILL.md")]
    assert [r["change"] for r in alpha] == ["added", "modified"]
    assert alpha[1]["commit"] == vendor_repo["merge"]
    assert alpha[1]["committed_at"].startswith("2026-03-01")
    assert alpha[1]["blob_sha"] == blob("alpha v2\n")
    assert alpha[1]["previous_blob_sha"] == blob("alpha v1\n")


def test_rename_is_delete_plus_add_with_the_same_blob(vendor_repo):
    rows = [r for r in changes(vendor_repo) if "gamma" in r["path"] and r["committed_at"].startswith("2026-04")]
    kinds = {r["path"]: r["change"] for r in rows}
    assert kinds == {"partner-built/gamma/SKILL.md": "deleted", "partner-built/gamma2/SKILL.md": "added"}
    assert len({r["blob_sha"] for r in rows}) == 1


def test_delete_keeps_the_last_blob(vendor_repo):
    d = [r for r in changes(vendor_repo) if r["change"] == "deleted" and "beta" in r["path"]][0]
    assert d["blob_sha"] == blob("beta v1\n")
    assert d["commit"] == vendor_repo["last"]


def test_rows_come_oldest_first(vendor_repo):
    dates = [r["committed_at"] for r in changes(vendor_repo)]
    assert dates == sorted(dates)


# ---------------------------------------------------------------- authorship

def by_path(rows, path, change=None):
    return next(r for r in rows if r["path"] == path and (change is None or r["change"] == change))


def test_authorship_from_nearest_manifest(vendor_repo):
    rows = changes(vendor_repo)
    a = by_path(rows, "plugins/core/skills/alpha/SKILL.md", "added")
    assert (a["authorship"], a["authorship_basis"], a["manifest_author"]) == ("first-party", "manifest", "Acme Inc")
    assert a["plugin_manifest"] == "plugins/core/.claude-plugin/plugin.json"
    b = by_path(rows, "plugins/guest/skills/beta/SKILL.md", "added")
    assert (b["authorship"], b["manifest_author"]) == ("other-author", "Globex")
    assert b["plugin_manifest"] == "plugins/guest/.codex-plugin/plugin.json"


def test_deleted_file_reads_manifest_before_the_delete(vendor_repo):
    d = by_path(changes(vendor_repo), "plugins/guest/skills/beta/SKILL.md", "deleted")
    assert d["manifest_author"] == "Globex"


def test_partner_path_and_unstated_and_placeholder(vendor_repo):
    rows = changes(vendor_repo)
    g = by_path(rows, "partner-built/gamma/SKILL.md", "added")
    assert (g["authorship"], g["authorship_basis"]) == ("other-author", "partner_path")
    root = by_path(rows, "SKILL.md")
    assert (root["authorship"], root["authorship_basis"]) == ("unstated", "none")
    t = by_path(rows, "templates/x/SKILL.md")
    assert t["manifest_author"] is None and t["authorship"] == "unstated"


@pytest.mark.parametrize("raw,expected", [
    ('{"author": {"name": " OpenAI "}}', "OpenAI"),
    ('{"author": "Your Name"}', None),
    ('{"author": ""}', None),
    ('{"name": "x"}', None),
    ("not json", None),
    ("[1, 2]", None),
])
def test_manifest_author(raw, expected):
    assert vr.manifest_author(raw) == expected


def test_classify_names_are_case_insensitive_substrings():
    assert vr.classify("OpenAI Codex", "p", ["OpenAI"], []) == ("first-party", "manifest")
    assert vr.classify("Vercel Labs", "p", ["OpenAI"], []) == ("other-author", "manifest")
    # A manifest author outranks a partner path.
    assert vr.classify("Acme", "partner-built/x", ["Acme"], ["partner-built/"]) == ("first-party", "manifest")


def test_symlinked_manifest_is_followed(vendor_repo):
    e = by_path(changes(vendor_repo), "plugins/linked/skills/eps/SKILL.md")
    assert e["plugin_manifest"] == "plugins/linked/.claude-plugin/plugin.json"
    assert (e["manifest_author"], e["authorship"]) == ("Acme Inc", "first-party")


def test_any_plugin_folder_counts(vendor_repo):
    z = by_path(changes(vendor_repo), "plugins/cur/skills/zeta/SKILL.md")
    assert z["plugin_manifest"] == "plugins/cur/.cursor-plugin/plugin.json"
    assert (z["manifest_author"], z["authorship"]) == ("Initech", "other-author")


def test_ancestor_dirs_nearest_first():
    assert vr.ancestor_dirs("a/b/SKILL.md") == ["a/b", "a", ""]
    assert vr.ancestor_dirs("SKILL.md") == [""]


def test_plugin_dirs_order_and_filter():
    entries = [("40000", ".plugin"), ("40000", ".zed-plugin"), ("40000", ".codex-plugin"),
               ("40000", ".claude-plugin"), ("100644", ".cursor-plugin"), ("40000", "plugin"),
               ("40000", ".github")]
    assert vr.plugin_dirs(entries) == [".claude-plugin", ".codex-plugin", ".plugin", ".zed-plugin"]


def test_dates_are_utc_and_sort_as_time(tmp_path):
    repo = tmp_path / "tz"
    repo.mkdir()
    sh(repo, "init", "-q", "-b", "main")
    write(repo, "a/SKILL.md", "a\n")
    commit(repo, "east", "2026-06-01T20:00:00+09:00")   # 11:00 UTC
    write(repo, "a/SKILL.md", "a2\n")
    commit(repo, "west", "2026-06-01T08:00:00-07:00")   # 15:00 UTC, earlier as local text
    rows = vr.skill_changes(repo)
    assert [r["committed_at"] for r in rows] == ["2026-06-01T11:00:00Z", "2026-06-01T15:00:00Z"]
    assert rows[0]["authored_at"] == "2026-06-01T11:00:00Z"


def _v(vendor, repo, path, sha, at, author=None, authorship="unstated", change="added"):
    return {"vendor": vendor, "repo": repo, "path": path, "skill_dir": path.rsplit("/", 1)[0],
            "blob_sha": sha, "committed_at": at, "change": change,
            "manifest_author": author, "authorship": authorship}


def test_cross_vendor_rows():
    versions = [
        _v("X", "x/r", "s/one/SKILL.md", "a" * 40, "2026-03-01T11:00:00Z"),
        _v("Y", "y/r", "p/one/SKILL.md", "a" * 40, "2026-03-01T15:00:00Z", "Y", "first-party"),
        _v("Y", "y/r", "q/one/SKILL.md", "a" * 40, "2026-04-01T00:00:00Z"),  # same vendor again: not a new copy
        _v("Z", "z/r", "two/SKILL.md", "b" * 40, "2026-05-01T00:00:00Z", change="deleted"),
        _v("X", "x/r", "two/SKILL.md", "b" * 40, "2026-06-01T00:00:00Z"),  # Z only had it as a delete
        _v("X", "x/r", "solo/SKILL.md", "c" * 40, "2026-01-01T00:00:00Z"),
    ]
    rows = vr.cross_vendor_rows(versions)
    assert len(rows) == 1
    r = rows[0]
    assert (r["origin_vendor"], r["copy_vendor"], r["copy_path"]) == ("X", "Y", "p/one/SKILL.md")
    assert r["same_day"] and r["copy_authorship"] == "first-party"
    s = vr.cross_vendor_summary(rows)
    assert s == {"copies": 1, "copy_skills": 1, "texts": 1, "same_day": 1,
                 "copy_manifest_names_copier": 1, "by_pair": {"X -> Y": 1}}


def test_removal_list_flags_blobs_and_skips_copy_repos(vendor_repo):
    from crawlers.exclusions import Exclusions
    ex = Exclusions({"bad/fork"}, {blob("alpha v1\n")})
    versions = vr.version_rows(CFG, changes(vendor_repo), ex)
    flagged = {v["path"] for v in versions if v["removal_listed"]}
    assert flagged == {"plugins/core/skills/alpha/SKILL.md"}
    occ = pa.table({"repo_full_name": ["bad/fork", "good/fork"], "path": ["SKILL.md"] * 2,
                    "blob_sha": [blob("eps\n")] * 2, "platform_folder": [None, None]})
    assert [m["copy_repo"] for m in vr.mirror_rows(versions, occ, ex)] == ["good/fork"]


# ---------------------------------------------------------------- tables

def test_skill_rows(vendor_repo):
    versions = vr.version_rows(CFG, changes(vendor_repo))
    skills = {s["path"]: s for s in vr.skill_rows(versions)}
    alpha = skills["plugins/core/skills/alpha/SKILL.md"]
    assert alpha["versions"] == 2 and alpha["present_at_head"]
    assert alpha["head_blob_sha"] == blob("alpha v2\n")
    assert alpha["skill_name"] == "alpha"
    beta = skills["plugins/guest/skills/beta/SKILL.md"]
    assert not beta["present_at_head"] and beta["head_blob_sha"] is None
    assert beta["authorship"] == "other-author"  # from its last live version
    assert skills["SKILL.md"]["skill_name"] is None


def test_mirror_rows_skip_vendor_repos_and_unknown_blobs(vendor_repo):
    versions = vr.version_rows(CFG, changes(vendor_repo))
    occ = pa.table({
        "repo_full_name": ["someone/fork", "ACME/skills", "other/x", "other/y"],
        "path": [".claude/skills/alpha/SKILL.md", "SKILL.md", "SKILL.md", "s/SKILL.md"],
        "blob_sha": [blob("alpha v1\n"), blob("root\n"), blob("unrelated\n"), blob("beta v1\n")],
        "platform_folder": ["claude", None, None, None],
    })
    rows = vr.mirror_rows(versions, occ)
    assert [r["copy_repo"] for r in rows] == ["someone/fork", "other/y"]
    assert rows[0]["vendor_path"] == "plugins/core/skills/alpha/SKILL.md"
    assert rows[0]["vendor_first_landed_at"].startswith("2026-01-01")
    assert rows[1]["blob_sha"] == blob("beta v1\n")  # a since-deleted vendor version still counts


def test_credit_prefers_the_vendors_own_publication():
    a, b, c = "a" * 40, "b" * 40, "c" * 40
    versions = [
        # a: a partner path published it first; the vendor's own copy, later, still gets the credit.
        _v("O", "o/plugins", "partner/x/SKILL.md", a, "2026-01-01T00:00:00Z",
           author="Jesse Vincent", authorship="other-author"),
        _v("A", "a/skills", "skills/x/SKILL.md", a, "2026-02-01T00:00:00Z",
           author="A", authorship="first-party"),
        # b: only ever published as someone else's work.
        _v("O", "o/plugins", "plugins/sp/SKILL.md", b, "2026-01-05T00:00:00Z",
           author="Jesse Vincent", authorship="other-author"),
        # c: two own publications; the earliest wins.
        _v("A", "a/skills", "late/SKILL.md", c, "2026-04-01T00:00:00Z"),
        _v("O", "o/skills", "early/SKILL.md", c, "2026-03-01T00:00:00Z"),
    ]
    credited = vr.credited_landings(versions)
    assert credited[a]["repo"] == "a/skills"
    assert credited[b]["path"] == "plugins/sp/SKILL.md"
    assert credited[c]["path"] == "early/SKILL.md"
    occ = pa.table({"repo_full_name": ["u/1", "u/2", "u/3"], "path": ["SKILL.md"] * 3,
                    "blob_sha": [a, b, c], "platform_folder": [None] * 3})
    rows = {r["blob_sha"]: r for r in vr.mirror_rows(versions, occ)}
    assert (rows[a]["vendor"], rows[a]["credit"], rows[a]["vendor_authorship"]) == ("A", "vendor", "first-party")
    assert (rows[b]["vendor"], rows[b]["credit"], rows[b]["vendor_manifest_author"]) == (
        "O", "repackaged", "Jesse Vincent")
    assert rows[c]["credit"] == "vendor" and rows[c]["vendor_authorship"] == "unstated"


# ---------------------------------------------------------------- config and run

def test_load_vendors_rejects_duplicates(tmp_path):
    p = tmp_path / "v.json"
    p.write_text(json.dumps({"vendors": {"A": {"repos": [{"repo": "a/x"}]},
                                         "B": {"repos": [{"repo": "A/X"}]}}}))
    with pytest.raises(ValueError):
        vr.load_vendors(p)


def test_shipped_vendor_list_loads():
    repos = vr.load_vendors()
    assert len(repos) >= 20
    assert all(r["names"] for r in repos)
    assert not any("community" in r["repo"] for r in repos)


def test_offline_needs_a_clone(tmp_path):
    with pytest.raises(FileNotFoundError):
        vr.clone_or_update("acme/skills", tmp_path / "missing", offline=True)


def test_run_end_to_end(vendor_repo, tmp_path):
    cfg = tmp_path / "vendors.json"
    cfg.write_text(json.dumps({"vendors": {"Acme": {"names": ["Acme"], "repos": [
        {"repo": "acme/skills", "license": "MIT", "partner_paths": ["partner-built/"]}]}}}))
    gs = tmp_path / "gitskills"
    gs.mkdir()
    pq.write_table(pa.table({
        "repo_full_name": ["someone/fork"], "path": ["SKILL.md"],
        "blob_sha": [blob("alpha v2\n")], "platform_folder": [None]}), gs / "occurrence.parquet")
    (gs / "manifest.json").write_text(json.dumps({"revision": "abc"}))
    exc = tmp_path / "exclusions.json"
    exc.write_text(json.dumps({"repos": [{"repo": "other/skills"}], "blobs": []}))
    cfg_doc = json.loads(cfg.read_text())
    cfg_doc["vendors"]["Other"] = {"repos": [{"repo": "other/skills"}]}  # on the removal list, never cloned
    cfg.write_text(json.dumps(cfg_doc))
    out = tmp_path / "out"
    m = vr.run(out=out, clones=vendor_repo["dir"].parent, vendors_path=cfg, offline=True,
               gitskills=gs, exclusions_path=exc)
    assert m["removal_list"]["stats"]["repos_excluded"] == ["other/skills"]
    assert m["cross_vendor"]["copies"] == 0
    assert m["repos"][0]["head"] == vendor_repo["last"]
    assert {k: m["mirror"][k] for k in ("gitskills_revision", "copies", "copy_repos",
                                        "vendor_blobs_copied", "copies_by_credit")} == {
        "gitskills_revision": "abc", "copies": 1, "copy_repos": 1, "vendor_blobs_copied": 1,
        "copies_by_credit": {"vendor": 1, "repackaged": 0}}
    assert m["mirror"]["credit_rule"].startswith("each text is credited")
    assert {o["path"] for o in m["outputs"]} == {"version.parquet", "skill.parquet",
                                              "cross_vendor.parquet", "mirror.parquet"}
    t = pq.read_table(out / "version.parquet")
    assert t.num_rows == m["summary"]["version_rows"]
    assert json.loads(t.schema.metadata[b"attribution"])["license"] == "CC-BY-4.0"
    assert "text" not in " ".join(t.column_names)  # pointers only
    saved = json.loads((out / "manifest.json").read_text())
    assert saved["summary"]["by_vendor"]["Acme"]["other-author"] >= 1
