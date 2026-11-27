import json
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from crawlers.atlas import delta as d


class FakeSearch:
    """A stand-in for GitHub code search over a list of (repo, path, sha, size) files.

    total_count can be scaled to imitate GitHub's undercounting, and queries can be
    made to fail."""

    def __init__(self, files, undercount=1.0, refuse=()):
        self.files, self.undercount, self.refuse = files, undercount, set(refuse)
        self.requests = 0
        self.queries = []

    def __call__(self, q, page):
        self.requests += 1
        self.queries.append((q, page))
        if q in self.refuse:
            raise d.SearchError(f"refused {q}")
        m = re.search(r"size:(\d+)(?:\.\.(\d+))?", q)
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        pm = re.search(r"path:(\S+)", q)
        hits = [f for f in self.files if lo <= f[3] <= hi
                and (pm is None or f[1].startswith(pm.group(1) + "/"))]
        start = (page - 1) * d.PER_PAGE
        visible = hits[:d.CAP]
        items = [{"repository": {"full_name": r}, "path": p, "sha": s}
                 for r, p, s, _ in visible[start:start + d.PER_PAGE]]
        return {"total_count": int(len(hits) * self.undercount), "incomplete_results": False,
                "items": items}


def _files(n, size_of=lambda i: i * 37 % d.MAX_SIZE, path_of=lambda i: f"skills/s{i}/SKILL.md"):
    return [(f"owner{i % 50}/repo{i}", path_of(i), f"{i:040x}", size_of(i)) for i in range(n)]


def _state(tmp_path):
    return d.open_state(tmp_path / ".cache" / "state.sqlite")


def _hits(db):
    return {(r, p) for r, p in db.execute("SELECT repo, path FROM hits")}


def test_split_parts_cover_range_without_gaps():
    for lo, hi, reported in ((0, d.MAX_SIZE, 50_000), (100, 103, 5000), (10, 11, 950), (0, 99, 901)):
        parts = d.split_parts(lo, hi, reported)
        assert parts[0][0] == lo and parts[-1][1] == hi
        assert all(b + 1 == c for (_, b), (c, _) in zip(parts, parts[1:]))
        assert 2 <= len(parts) <= d.MAX_PARTS


def test_query_for():
    assert d.query_for(5, 5, "") == "filename:SKILL.md size:5"
    assert d.query_for(0, 9, "path:.claude") == "filename:SKILL.md size:0..9 path:.claude"


def test_small_crawl_finishes_in_one_query(tmp_path):
    files = _files(250)
    db, s = _state(tmp_path), FakeSearch(files)
    assert d.crawl(db, s, log=lambda m: None)
    assert _hits(db) == {(r, p) for r, p, _, _ in files}
    assert s.requests == 3  # three pages of 100, 100, 50


def test_large_crawl_splits_until_every_range_is_under_the_cap(tmp_path):
    files = _files(5000)
    db, s = _state(tmp_path), FakeSearch(files)
    assert d.crawl(db, s, log=lambda m: None)
    assert _hits(db) == {(r, p) for r, p, _, _ in files}
    status = dict(db.execute("SELECT status, COUNT(*) FROM ranges GROUP BY status").fetchall())
    assert status.get("split", 0) >= 1 and "capped" not in status and "todo" not in status


def test_undercounted_total_still_splits_when_paging_hits_the_cap(tmp_path):
    files = _files(2500)
    db, s = _state(tmp_path), FakeSearch(files, undercount=0.1)  # reports 250 for 2,500
    assert d.crawl(db, s, log=lambda m: None)
    assert _hits(db) == {(r, p) for r, p, _, _ in files}


def test_one_size_over_the_cap_is_capped_and_retried_by_path(tmp_path):
    # 1,300 copies of one text at one size: 700 under .claude, 600 under skills
    files = _files(1300, size_of=lambda i: 4242,
                   path_of=lambda i: (".claude" if i < 700 else "skills") + f"/skills/x{i}/SKILL.md")
    db, s = _state(tmp_path), FakeSearch(files)
    assert d.crawl(db, s, log=lambda m: None)
    capped = db.execute("SELECT lo, hi, extra FROM ranges WHERE status = 'capped'").fetchall()
    assert (4242, 4242, "") in capped
    assert _hits(db) == {(r, p) for r, p, _, _ in files}  # the path queries found the rest


def test_refused_query_marks_range_failed_and_moves_on(tmp_path):
    files = _files(10)
    s = FakeSearch(files, refuse={d.query_for(0, d.MAX_SIZE, "")})
    db = _state(tmp_path)
    logs = []
    assert d.crawl(db, s, log=logs.append)
    assert db.execute("SELECT status FROM ranges").fetchall() == [("failed",)]
    assert any("refused" in m for m in logs)


def test_max_requests_stops_and_a_rerun_resumes(tmp_path):
    files = _files(3000)
    db, s = _state(tmp_path), FakeSearch(files)
    assert not d.crawl(db, s, max_requests=4, log=lambda m: None)
    first = s.requests
    db.close()
    db2, s2 = _state(tmp_path), FakeSearch(files)  # a fresh process: new client, same state
    assert d.crawl(db2, s2, log=lambda m: None)
    assert _hits(db2) == {(r, p) for r, p, _, _ in files}
    assert db2.execute("SELECT COUNT(*) FROM ranges WHERE lo = 0 AND hi = ? AND extra = ''",
                       (d.MAX_SIZE,)).fetchone()[0] == 1
    assert first >= 4


def test_platform_folder():
    assert d.platform_folder(".claude/skills/a/SKILL.md") == "claude"
    assert d.platform_folder("x/.codex/skills/SKILL.md") == "codex"
    assert d.platform_folder("skills/a/SKILL.md") == "other"


def test_diff_classifies_new_texts_new_copies_changes_and_gone():
    gitskills = [
        {"repo_full_name": "a/one", "path": "skills/x/SKILL.md", "blob_sha": "1" * 40},
        {"repo_full_name": "a/one", "path": "skills/y/SKILL.md", "blob_sha": "2" * 40},
        {"repo_full_name": "b/gone", "path": "SKILL.md", "blob_sha": "3" * 40},
        {"repo_full_name": "c/removed", "path": "SKILL.md", "blob_sha": "4" * 40},
    ]
    hits = [
        {"repo": "A/One", "path": "skills/x/SKILL.md", "sha": "1" * 40, "lo": 0, "hi": 9},   # unchanged
        {"repo": "a/one", "path": "skills/y/SKILL.md", "sha": "5" * 40, "lo": 0, "hi": 9},   # changed
        {"repo": "d/copy", "path": ".claude/skills/x/skill.md", "sha": "1" * 40, "lo": 0, "hi": 9},  # new copy
        {"repo": "e/new", "path": "SKILL.md", "sha": "6" * 40, "lo": 0, "hi": 9},            # new text
        {"repo": "c/removed", "path": "SKILL.md", "sha": "4" * 40, "lo": 0, "hi": 9},        # excluded repo
    ]
    ex = d.removal.Exclusions(repos={"c/removed"}, blobs={"6" * 40})
    rows, gone, counts = d.diff(hits, gitskills, ex)
    by = {(r["repo_full_name"], r["path"]): r for r in rows}
    assert ("c/removed", "SKILL.md") not in by
    assert not by[("A/One", "skills/x/SKILL.md")]["new_occurrence"]
    changed = by[("a/one", "skills/y/SKILL.md")]
    assert changed["new_text"] and changed["previous_blob_sha"] == "2" * 40
    copy = by[("d/copy", ".claude/skills/x/skill.md")]
    assert copy["new_occurrence"] and not copy["new_text"] and copy["platform_folder"] == "claude"
    assert by[("e/new", "SKILL.md")]["removal_listed"]
    assert [g["repo_full_name"] for g in gone] == ["b/gone"]
    assert counts["new_texts"] == 2 and counts["changed_in_place"] == 1
    assert counts["new_occurrences_of_known_texts"] == 1 and counts["gone"] == 1
    assert counts["basename_not_exact"] == 0  # basenames compare case-insensitively


def test_finish_writes_outputs_and_flags_unreliable_gone(tmp_path):
    files = _files(1200, size_of=lambda i: 77)  # one size over the cap, no path matches
    db, s = _state(tmp_path), FakeSearch(files)
    complete = d.crawl(db, s, log=lambda m: None)
    gs = tmp_path / "gitskills"
    gs.mkdir()
    pq.write_table(pa.table({"repo_full_name": ["owner0/repo0", "z/old"],
                             "path": ["skills/s0/SKILL.md", "SKILL.md"],
                             "blob_sha": [f"{0:040x}", "9" * 40]}), gs / "occurrence.parquet")
    (gs / "manifest.json").write_text(json.dumps({"revision": "abc123"}))
    ex = tmp_path / "ex.json"
    ex.write_text(json.dumps({"repos": [], "blobs": []}))
    out = tmp_path / "out"
    m = d.finish(db, out, gs, ex, s.requests, complete)
    assert m["complete"] and not m["gone_is_reliable"]
    assert m["capped_ranges"][0]["size"] == "77..77"
    assert m["compared_with"]["gitskills_revision"] == "abc123"
    assert {o["path"] for o in m["outputs"]} == {"occurrence.parquet", "gone.parquet"}
    assert pq.read_table(out / "gone.parquet").num_rows == 1
    assert json.loads((out / "manifest.json").read_text())["method_version"] == d.METHOD_VERSION


def test_main_needs_the_gitskills_import(tmp_path, capsys):
    assert d.main(["--gitskills", str(tmp_path), "--out", str(tmp_path / "o"), "--finish-only"]) == 2
    assert "GitSkills import first" in capsys.readouterr().err


def test_client_paces_and_retries_on_rate_limit(monkeypatch):
    import io
    import urllib.error

    t = [0.0]
    sleeps = []

    def sleep(s):
        sleeps.append(s)
        t[0] += s

    calls = []

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def urlopen(req, timeout):
        calls.append(req.full_url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 403, "rate", {"Retry-After": "30"}, None)
        return Resp(b'{"total_count": 0, "items": []}')

    monkeypatch.setattr(d.urllib.request, "urlopen", urlopen)
    c = d.GitHubSearch("tok", min_interval=6.5, sleep=sleep, clock=lambda: t[0])
    assert c("filename:SKILL.md size:1", 1)["total_count"] == 0
    assert c.requests == 2 and 31 in sleeps
    c("filename:SKILL.md size:2", 1)
    assert c.requests == 3 and sleeps[-1] == pytest.approx(6.5)


def test_client_raises_on_422(monkeypatch):
    import urllib.error

    def urlopen(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 422, "bad", {}, None)

    monkeypatch.setattr(d.urllib.request, "urlopen", urlopen)
    with pytest.raises(d.SearchError):
        d.GitHubSearch("tok", sleep=lambda s: None, clock=lambda: 0.0)("q", 1)
