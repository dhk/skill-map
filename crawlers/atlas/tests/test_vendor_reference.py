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


def test_manifest_candidates_nearest_first():
    c = vr.manifest_candidates("a/b/SKILL.md")
    assert c[:2] == ["a/b/.claude-plugin/plugin.json", "a/b/.codex-plugin/plugin.json"]
    assert c[-1] == ".codex-plugin/plugin.json"
    assert vr.manifest_candidates("SKILL.md") == [".claude-plugin/plugin.json", ".codex-plugin/plugin.json"]


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
    out = tmp_path / "out"
    m = vr.run(out=out, clones=vendor_repo["dir"].parent, vendors_path=cfg, offline=True, gitskills=gs)
    assert m["repos"][0]["head"] == vendor_repo["last"]
    assert m["mirror"] == {"gitskills_revision": "abc", "copies": 1, "copy_repos": 1, "vendor_blobs_copied": 1}
    assert {o["path"] for o in m["outputs"]} == {"version.parquet", "skill.parquet", "mirror.parquet"}
    t = pq.read_table(out / "version.parquet")
    assert t.num_rows == m["summary"]["version_rows"]
    assert json.loads(t.schema.metadata[b"attribution"])["license"] == "CC-BY-4.0"
    assert "text" not in " ".join(t.column_names)  # pointers only
    saved = json.loads((out / "manifest.json").read_text())
    assert saved["summary"]["by_vendor"]["Acme"]["other-author"] >= 1
