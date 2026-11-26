import json
import types
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from crawlers.atlas import gitskills as g


def _artifacts():
    rows = [
        # repo, path, sha, primary, description
        ("anthropics/skills", "skills/pdf/SKILL.md", "a" * 40, 1, "Use when working with PDFs."),
        ("someone/mirror", ".claude/skills/pdf/SKILL.md", "a" * 40, 0, "Use when working with PDFs."),
        ("other/app", ".codex/skills/deploy/SKILL.md", "b" * 40, 1, "x" * 400),
        ("other/app", "docs/notes/SKILL.md", "c" * 40, 1, None),
    ]
    n = len(rows)
    data = {c: [None] * n for c in g.ARTIFACT_COLUMNS}
    data["repo_full_name"] = [r[0] for r in rows]
    data["path"] = [r[1] for r in rows]
    data["filename"] = ["SKILL.md"] * n
    data["location_class"] = ["catalog", "operational", "operational", "other"]
    data["file_sha"] = [r[2] for r in rows]
    data["dedup_primary"] = [r[3] for r in rows]
    data["description"] = [r[4] for r in rows]
    data["name"] = ["pdf", "pdf", "deploy", None]
    data["history_fetched"] = [1, 0, 0, 0]
    data["first_commit_at"] = ["2025-12-01T00:00:00Z", None, None, None]
    types = {c: pa.int64() for c in ("content_fetched", "frontmatter_valid", "body_chars",
                                    "history_fetched", "dedup_primary", "commit_count",
                                    "sibling_count", "has_scripts", "has_references")}
    return pa.table({c: pa.array(v, types.get(c, pa.string())) for c, v in data.items()})


def _repos():
    return pa.table({
        "full_name": ["anthropics/skills", "someone/mirror", "other/app"],
        "owner": ["anthropics", "someone", "other"],
        "stars": pa.array([100, 1, 5], pa.int64()),
        "forks": pa.array([10, 0, 0], pa.int64()),
        "is_fork": pa.array([0, 0, 0], pa.int64()),
        "language": ["Python", None, "Go"],
        "license": ["apache-2.0", None, "AGPL-3.0"],
        "description": [None, None, None],
        "created_at": ["2025-10-01T00:00:00Z"] * 3,
        "pushed_at": ["2026-07-01T00:00:00Z"] * 3,
    })


@pytest.mark.parametrize("path,expected", [
    (".claude/skills/x/SKILL.md", "claude"),
    ("pkg/.codex/skills/x/SKILL.md", "codex"),
    (".agents/skills/x/SKILL.md", "agents"),
    ("skills/x/SKILL.md", "other"),
    (".claude", "other"),
    (None, "other"),
])
def test_platform_folder(path, expected):
    assert g.platform_folder(path) == expected


def test_build_tables_shapes_and_policy():
    t = g.build_tables(_artifacts(), _repos(), "gitskills@test")
    assert t["occurrence"].num_rows == 4
    assert t["content"].num_rows == 3  # one per dedup_primary row
    assert t["repo"].num_rows == 3
    assert "content" not in t["content"].column_names  # never carry full text
    assert t["occurrence"].column("platform_folder").to_pylist() == ["other", "claude", "codex", "other"]
    c = t["content"]
    # Descriptions only where the earliest copy's licence is on the allow-list.
    assert c.column("description_excerpt").to_pylist() == ["Use when working with PDFs.", None, None]
    assert c.column("description_withheld").to_pylist() == [None, "licence", "licence"]
    assert c.column("content_license_spdx").to_pylist() == ["Apache-2.0", None, None]
    assert c.column("license_from_repo").to_pylist() == ["anthropics/skills", "other/app", "other/app"]
    assert t["repo"].column("license_permits_text").to_pylist() == [True, False, False]


def _with_repo_license(name, licence):
    r = _repos().to_pydict()
    r["license"][r["full_name"].index(name)] = licence
    return pa.table(r, schema=_repos().schema)


def test_long_description_truncated_when_licence_allows():
    t = g.build_tables(_artifacts(), _with_repo_license("other/app", "MIT"), "t")
    desc = t["content"].column("description_excerpt").to_pylist()
    assert len(desc[1]) == g.EXCERPT_LIMIT
    assert t["content"].column("description_truncated").to_pylist() == [False, True, False]


def test_earliest_copy_licence_wins():
    a = _artifacts().to_pydict()
    a["first_commit_at"][1] = "2025-11-01T00:00:00Z"  # the unlicensed mirror is older
    t = g.build_tables(pa.table(a, schema=_artifacts().schema), _repos(), "t")
    c = t["content"]
    assert c.column("license_from_repo").to_pylist()[0] == "someone/mirror"
    assert c.column("description_withheld").to_pylist()[0] == "licence"


def test_earliest_copy_falls_back_to_repo_creation():
    a = _artifacts().to_pydict()
    a["first_commit_at"] = [None] * 4
    r = _repos().to_pydict()
    r["created_at"][1] = "2025-01-01T00:00:00Z"  # mirror repo created first
    lic = g.earliest_copy_licence(pa.table(a, schema=_artifacts().schema),
                                  pa.table(r, schema=_repos().schema))
    assert lic["a" * 40] == (None, "someone/mirror")


def test_removal_list_drops_repo_and_reassigns_representative():
    ex = g.removal.Exclusions(repos={"Anthropics/Skills"}, blobs=set())
    t = g.build_tables(_artifacts(), _repos(), "t", ex)
    assert t["occurrence"].num_rows == 3
    assert t["repo"].num_rows == 2
    assert t["content"].num_rows == 3
    assert t["content"].column("representative_repo").to_pylist()[0] == "someone/mirror"
    assert "anthropics/skills" not in [r.lower() for r in t["occurrence"].column("repo_full_name").to_pylist()]


def test_removal_list_blob_keeps_pointer_only():
    ex = g.removal.Exclusions(repos=set(), blobs={"a" * 40})
    c = g.build_tables(_artifacts(), _repos(), "t", ex)["content"]
    assert c.column("blob_sha").to_pylist()[0] == "a" * 40
    assert c.column("name").to_pylist()[0] is None
    assert c.column("description_excerpt").to_pylist()[0] is None
    assert c.column("description_withheld").to_pylist()[0] == "removal-list"


def test_tables_carry_cc_by_attribution():
    t = g.build_tables(_artifacts(), _repos(), "t")
    for table in t.values():
        meta = table.schema.metadata
        assert meta[b"license"] == b"CC-BY-4.0"
        assert b"GitSkills" in meta[b"attribution"]


def test_summarise_counts_overlap():
    t = g.build_tables(_artifacts(), _repos(), "gitskills@test")
    s = g.summarise(t, {"a" * 40, "z" * 40})
    assert s["distinct_blob_shas"] == 3
    assert s["contents_whose_representative_repo_permits_text"] == 1
    assert s["skillmap_blob_shas_found_in_gitskills"] == 1
    assert s["platform_folder"]["other"] == 2


def _write_local(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    (data / "artifacts").mkdir(parents=True)
    (data / "repos").mkdir()
    pq.write_table(_artifacts(), data / "artifacts" / "part-0.parquet")
    pq.write_table(_repos(), data / "repos" / "part-0.parquet")
    return data


def _empty_skillmap(tmp_path: Path) -> Path:
    root = tmp_path / "skillmap"
    (root / "crawls").mkdir(parents=True)
    return root


def test_run_local_writes_tables_and_manifest(tmp_path: Path):
    data = _write_local(tmp_path)
    out = tmp_path / "out"
    m = g.run(out, local=data, check_counts=False, skillmap_root=_empty_skillmap(tmp_path))
    assert set(m["outputs"]) == {"occurrence", "content", "repo"}
    assert (out / "manifest.json").exists()
    saved = json.loads((out / "manifest.json").read_text())
    assert saved["inputs"]["artifacts"][0]["sha256"]
    assert pq.read_table(out / "content.parquet").num_rows == 3
    assert saved["source"]["revision"] == "local"
    assert str(tmp_path) not in (out / "manifest.json").read_text()


def test_run_requires_removal_list(tmp_path: Path):
    data = _write_local(tmp_path)
    with pytest.raises(FileNotFoundError):
        g.run(tmp_path / "out", local=data, check_counts=False,
              skillmap_root=_empty_skillmap(tmp_path), exclusions_path=tmp_path / "missing.json")


def test_run_local_records_removal_and_attribution(tmp_path: Path):
    data = _write_local(tmp_path)
    ex = tmp_path / "ex.json"
    ex.write_text(json.dumps({"repos": [{"repo": "someone/mirror"}], "blobs": []}))
    out = tmp_path / "out"
    m = g.run(out, local=data, check_counts=False, skillmap_root=_empty_skillmap(tmp_path),
              exclusions_path=ex)
    assert m["removal_list"]["repos_excluded"] == 1
    assert m["removal_list"]["occurrences_dropped"] == 1
    assert m["attribution"]["license"] == "CC-BY-4.0"
    assert pq.read_schema(out / "content.parquet").metadata[b"license"] == b"CC-BY-4.0"


def test_run_local_rejects_wrong_counts(tmp_path: Path):
    data = _write_local(tmp_path)
    with pytest.raises(SystemExit):
        g.run(tmp_path / "out", local=data, check_counts=True, skillmap_root=_empty_skillmap(tmp_path))


def test_license_case_insensitive():
    assert g.license_permits_text("mit")
    assert g.license_permits_text(" Apache-2.0 ")
    assert not g.license_permits_text("NOASSERTION")
    assert not g.license_permits_text(None)


def test_duplicate_representative_rejected():
    a = _artifacts().to_pydict()
    a["dedup_primary"][1] = 1  # second representative for the same blob SHA
    with pytest.raises(ValueError, match="more than one representative"):
        g.build_tables(pa.table(a, schema=_artifacts().schema), _repos(), "t")


def test_empty_sha_representative_rejected():
    a = _artifacts().to_pydict()
    a["file_sha"][3] = ""
    with pytest.raises(ValueError, match="empty blob SHA"):
        g.build_tables(pa.table(a, schema=_artifacts().schema), _repos(), "t")


def test_duplicate_occurrence_id_rejected():
    a = _artifacts().to_pydict()
    a["path"][3] = a["path"][2]
    with pytest.raises(ValueError, match="duplicate repo\\+path"):
        g.build_tables(pa.table(a, schema=_artifacts().schema), _repos(), "t")


def test_orphan_repo_rejected():
    r = _repos().to_pydict()
    r["full_name"][2] = "other/renamed"
    with pytest.raises(ValueError, match="no row in repos"):
        g.build_tables(_artifacts(), pa.table(r, schema=_repos().schema), "t")


def test_repo_name_match_case_insensitive():
    r = _repos().to_pydict()
    r["full_name"][0] = "Anthropics/Skills"
    t = g.build_tables(_artifacts(), pa.table(r, schema=_repos().schema), "t")
    s = g.summarise(t, set())
    assert s["contents_whose_representative_repo_permits_text"] == 1


def test_empty_shas_not_counted_distinct():
    a = _artifacts().to_pydict()
    a["file_sha"][1] = None  # a non-representative occurrence without a SHA
    t = g.build_tables(pa.table(a, schema=_artifacts().schema), _repos(), "t")
    assert g.summarise(t, set())["distinct_blob_shas"] == 3


def test_concat_tolerates_null_typed_shard(tmp_path: Path):
    data = _write_local(tmp_path)
    base = _repos().to_pydict()
    base["description"] = ["a", "b", "c"]
    pq.write_table(pa.table(base), data / "repos" / "part-0.parquet")  # description: string
    rows = _repos().slice(0, 1).to_pydict()
    rows["description"] = [None]
    shard = pa.table({k: v for k, v in rows.items()})  # description typed as null
    assert shard.schema.field("description").type == pa.null()
    rows["full_name"] = ["extra/repo"]
    pq.write_table(pa.table(rows), data / "repos" / "part-1.parquet")
    table, _ = g.read_local(data, "repos", g.REPO_COLUMNS)
    assert table.num_rows == 4
    assert table.schema.field("description").type == pa.string()


# --- remote read with a fake Hugging Face connection ---------------------------

class _FakeFS:
    def __init__(self, files):
        self.files = files
        self.opened = []

    def open(self, path, mode="rb"):
        self.opened.append(path)
        return open(self.files[path.split("@", 1)[1].split("/", 1)[1]], mode)


def _fake_hub(monkeypatch, tmp_path, sha):
    import huggingface_hub

    data = _write_local(tmp_path)
    files = {f"data/artifacts/part-0.parquet": data / "artifacts" / "part-0.parquet",
             f"data/repos/part-0.parquet": data / "repos" / "part-0.parquet"}
    siblings = [types.SimpleNamespace(rfilename=k, size=v.stat().st_size,
                                      lfs=types.SimpleNamespace(sha256="f" * 64))
                for k, v in files.items()]
    siblings.append(types.SimpleNamespace(rfilename="README.md", size=1, lfs=None))
    fs = _FakeFS(files)

    class FakeApi:
        def dataset_info(self, repo_id, revision=None, files_metadata=False):
            return types.SimpleNamespace(sha=sha, siblings=siblings)

    monkeypatch.setattr(huggingface_hub, "HfApi", FakeApi)
    monkeypatch.setattr(huggingface_hub, "HfFileSystem", lambda: fs)
    return fs


def test_remote_read_uses_pinned_commit(monkeypatch, tmp_path):
    pin = json.loads(g.SOURCES.read_text())["gitskills"]["hf_revision"]
    full = pin + "0" * (40 - len(pin))
    fs = _fake_hub(monkeypatch, tmp_path, full)
    m = g.run(tmp_path / "out", check_counts=False, skillmap_root=_empty_skillmap(tmp_path))
    assert m["source"]["revision"] == full
    assert all(f"@{full}/" in p for p in fs.opened)
    assert m["inputs"]["artifacts"][0]["sha256"] == "f" * 64
    assert m["outputs"]["content"]["rows"] == 3


def test_remote_read_resumes_from_saved_columns(monkeypatch, tmp_path):
    pin = json.loads(g.SOURCES.read_text())["gitskills"]["hf_revision"]
    full = pin + "0" * (40 - len(pin))
    fs = _fake_hub(monkeypatch, tmp_path, full)
    out = tmp_path / "out"
    root = _empty_skillmap(tmp_path)
    g.run(out, check_counts=False, skillmap_root=root)
    assert len(fs.opened) == 2
    fs.opened.clear()
    m = g.run(out, check_counts=False, skillmap_root=root)
    assert fs.opened == []  # both files came from the saved columns
    assert m["outputs"]["content"]["rows"] == 3
    # A different column list must not reuse the saved file.
    info = g.resolve_revision("x/y", pin)
    g.read_remote("x/y", info, "repos", g.REPO_COLUMNS[:3], out / ".cache")
    assert len(fs.opened) == 1


def test_remote_read_rejects_wrong_commit(monkeypatch, tmp_path):
    _fake_hub(monkeypatch, tmp_path, "deadbeef" + "0" * 32)
    with pytest.raises(SystemExit, match="refusing"):
        g.run(tmp_path / "out", check_counts=False, skillmap_root=_empty_skillmap(tmp_path))
