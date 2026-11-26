import json
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
        "license": ["Apache-2.0", None, "AGPL-3.0"],
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
    desc = t["content"].column("description_excerpt").to_pylist()
    assert len(desc[1]) == g.EXCERPT_LIMIT
    assert t["content"].column("description_truncated").to_pylist() == [False, True, False]
    assert t["repo"].column("license_permits_text").to_pylist() == [True, False, False]


def test_summarise_counts_overlap():
    t = g.build_tables(_artifacts(), _repos(), "gitskills@test")
    s = g.summarise(t, {"a" * 40, "z" * 40})
    assert s["distinct_blob_shas"] == 3
    assert s["contents_whose_representative_repo_permits_text"] == 1
    assert s["skillmap_blob_shas_found_in_gitskills"] == 1
    assert s["platform_folder"]["other"] == 2


def test_run_local_writes_tables_and_manifest(tmp_path: Path):
    data = tmp_path / "data"
    (data / "artifacts").mkdir(parents=True)
    (data / "repos").mkdir()
    pq.write_table(_artifacts(), data / "artifacts" / "part-0.parquet")
    pq.write_table(_repos(), data / "repos" / "part-0.parquet")
    out = tmp_path / "out"
    m = g.run(out, local=data, check_counts=False)
    assert set(m["outputs"]) == {"occurrence", "content", "repo"}
    assert (out / "manifest.json").exists()
    saved = json.loads((out / "manifest.json").read_text())
    assert saved["inputs"]["artifacts"][0]["sha256"]
    assert pq.read_table(out / "content.parquet").num_rows == 3


def test_run_local_rejects_wrong_counts(tmp_path: Path):
    data = tmp_path / "data"
    (data / "artifacts").mkdir(parents=True)
    (data / "repos").mkdir()
    pq.write_table(_artifacts(), data / "artifacts" / "part-0.parquet")
    pq.write_table(_repos(), data / "repos" / "part-0.parquet")
    with pytest.raises(SystemExit):
        g.run(tmp_path / "out", local=data, check_counts=True)
