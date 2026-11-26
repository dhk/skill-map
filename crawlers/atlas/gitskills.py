"""Import GitSkills metadata as the Atlas base catalogue.

Reads only the metadata columns of the pinned GitSkills release (never the
`content` text or commit messages) and writes three lowest-grain tables:

- occurrence: one row per SKILL.md occurrence (repo, path, blob SHA, ...)
- content:    one row per distinct blob SHA, from the GitSkills representative
- repo:       one row per repository

Parquet outputs are kept out of git (see data/atlas/.gitignore). The small
manifest.json, with the resolved revision, input file hashes, row counts and
output hashes, is meant to be committed after a run so every later step can
cite exactly what it used.

Usage:
    python -m crawlers.atlas.gitskills                  # remote, pinned revision
    python -m crawlers.atlas.gitskills --local DIR      # a local copy of data/
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

METHOD_VERSION = "gitskills-import/1.0.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES = Path(__file__).with_name("sources.json")
DEFAULT_OUT = REPO_ROOT / "data" / "atlas" / "gitskills"

# Metadata only. `content`, commit messages and author codes are left out on
# purpose: the text stays under origin licenses (DATA-POLICY.md) and the
# author codes are not needed for the catalogue.
ARTIFACT_COLUMNS = [
    "repo_full_name", "path", "filename", "location_class", "file_sha",
    "discovered_at", "content_fetched", "frontmatter_valid", "name",
    "description", "body_chars", "history_fetched", "dedup_primary",
    "first_commit_at", "last_commit_at", "commit_count", "sibling_count",
    "has_scripts", "has_references", "first_commit_author_type",
]
REPO_COLUMNS = [
    "full_name", "owner", "stars", "forks", "is_fork", "language", "license",
    "description", "created_at", "pushed_at",
]

# Agent platform inferred from the folder a skill sits under.
PLATFORM_FOLDERS = {
    ".claude": "claude", ".codex": "codex", ".agents": "agents",
    ".github": "github", ".cursor": "cursor", ".gemini": "gemini",
    ".windsurf": "windsurf", ".opencode": "opencode", ".kiro": "kiro",
}

# Licenses that allow redistribution of the text with attribution. Compared
# case-insensitively, since repo metadata is not consistent about case.
PERMISSIVE_LICENSES = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD",
    "Unlicense", "CC0-1.0", "CC-BY-4.0", "MIT-0", "Zlib", "BSL-1.0",
}
_PERMISSIVE_LOWER = {l.lower() for l in PERMISSIVE_LICENSES}


def license_permits_text(license_id: str | None) -> bool:
    return bool(license_id) and license_id.strip().lower() in _PERMISSIVE_LOWER


def _norm_repo(name: str | None) -> str:
    return (name or "").strip().lower()


def _non_empty(values) -> list:
    return [v for v in values if v not in (None, "")]

EXCERPT_LIMIT = 300  # characters, per DATA-POLICY.md


def platform_folder(path: str | None) -> str:
    """Return the agent platform implied by the first dot-folder in a path."""
    if not path:
        return "other"
    for part in path.split("/")[:-1]:
        if part in PLATFORM_FOLDERS:
            return PLATFORM_FOLDERS[part]
    return "other"


def _truncate(values: pa.ChunkedArray | pa.Array) -> tuple[pa.Array, pa.Array]:
    py = values.to_pylist()
    out, flag = [], []
    for v in py:
        if v is not None and len(v) > EXCERPT_LIMIT:
            out.append(v[:EXCERPT_LIMIT])
            flag.append(True)
        else:
            out.append(v)
            flag.append(False)
    return pa.array(out, pa.string()), pa.array(flag, pa.bool_())


def check_keys(artifacts: pa.Table, repos: pa.Table) -> None:
    """Fail loudly if the keys the Atlas relies on are not unique or not joined."""
    repo_names = repos.column("full_name").to_pylist()
    norm_repos = [_norm_repo(r) for r in repo_names]
    if len(set(norm_repos)) != len(norm_repos):
        raise ValueError(f"repos: {len(norm_repos) - len(set(norm_repos))} duplicate repo names")

    occ_repos = artifacts.column("repo_full_name").to_pylist()
    ids = [f"{_norm_repo(r)}:{p}" for r, p in zip(occ_repos, artifacts.column("path").to_pylist())]
    if len(set(ids)) != len(ids):
        raise ValueError(f"artifacts: {len(ids) - len(set(ids))} duplicate repo+path ids")

    known = set(norm_repos)
    orphans = {_norm_repo(r) for r in occ_repos} - known
    if orphans:
        raise ValueError(f"artifacts: {len(orphans)} repos with no row in repos, e.g. {sorted(orphans)[:3]}")

    primary = artifacts.filter(pc.equal(artifacts.column("dedup_primary"), 1))
    shas = primary.column("file_sha").to_pylist()
    if len(_non_empty(shas)) != len(shas):
        raise ValueError(f"artifacts: {len(shas) - len(_non_empty(shas))} representative rows with an empty blob SHA")
    if len(set(shas)) != len(shas):
        raise ValueError(f"artifacts: {len(shas) - len(set(shas))} blob SHAs with more than one representative row")


def build_tables(artifacts: pa.Table, repos: pa.Table, source: str) -> dict[str, pa.Table]:
    """Turn GitSkills artifacts and repos into occurrence, content and repo tables."""
    check_keys(artifacts, repos)
    paths = artifacts.column("path").to_pylist()
    occurrence = pa.table({
        "occurrence_id": pa.array(
            [f"{r}:{p}" for r, p in zip(artifacts.column("repo_full_name").to_pylist(), paths)],
            pa.string()),
        "repo_full_name": artifacts.column("repo_full_name"),
        "path": artifacts.column("path"),
        "filename": artifacts.column("filename"),
        "blob_sha": artifacts.column("file_sha"),
        "location_class": artifacts.column("location_class"),
        "platform_folder": pa.array([platform_folder(p) for p in paths], pa.string()),
        "discovered_at": artifacts.column("discovered_at"),
        "source": pa.array([source] * artifacts.num_rows, pa.string()),
        "method_version": pa.array([METHOD_VERSION] * artifacts.num_rows, pa.string()),
    })

    reps = artifacts.filter(pc.equal(artifacts.column("dedup_primary"), 1))
    description, truncated = _truncate(reps.column("description"))
    content = pa.table({
        "blob_sha": reps.column("file_sha"),
        "representative_repo": reps.column("repo_full_name"),
        "representative_path": reps.column("path"),
        "name": reps.column("name"),
        "description_excerpt": description,
        "description_truncated": truncated,
        "frontmatter_valid": reps.column("frontmatter_valid"),
        "body_chars": reps.column("body_chars"),
        "has_scripts": reps.column("has_scripts"),
        "has_references": reps.column("has_references"),
        "sibling_count": reps.column("sibling_count"),
        "history_fetched": reps.column("history_fetched"),
        "first_commit_at": reps.column("first_commit_at"),
        "last_commit_at": reps.column("last_commit_at"),
        "commit_count": reps.column("commit_count"),
        "first_commit_author_type": reps.column("first_commit_author_type"),
        "source": pa.array([source] * reps.num_rows, pa.string()),
        "method_version": pa.array([METHOD_VERSION] * reps.num_rows, pa.string()),
    })

    licenses = repos.column("license").to_pylist()
    repo = pa.table({
        "repo_full_name": repos.column("full_name"),
        "owner": repos.column("owner"),
        "stars": repos.column("stars"),
        "forks": repos.column("forks"),
        "is_fork": repos.column("is_fork"),
        "language": repos.column("language"),
        "license": repos.column("license"),
        "license_permits_text": pa.array([license_permits_text(l) for l in licenses], pa.bool_()),
        "description": repos.column("description"),
        "created_at": repos.column("created_at"),
        "pushed_at": repos.column("pushed_at"),
        "source": pa.array([source] * repos.num_rows, pa.string()),
        "method_version": pa.array([METHOD_VERSION] * repos.num_rows, pa.string()),
    })
    return {"occurrence": occurrence, "content": content, "repo": repo}


def _counts(table: pa.Table, column: str) -> dict[str, int]:
    vc = pc.value_counts(table.column(column).fill_null("null")).to_pylist()
    return dict(sorted(((d["values"], d["counts"]) for d in vc), key=lambda kv: -kv[1]))


def skillmap_blob_shas(root: Path = REPO_ROOT) -> set[str]:
    """Blob SHAs present in this repo's own crawl snapshots."""
    shas: set[str] = set()
    for f in sorted(glob.glob(str(root / "crawls" / "*" / "data.json"))):
        with open(f) as fh:
            for row in json.load(fh).get("results", []):
                if row.get("file_sha"):
                    shas.add(row["file_sha"])
    return shas


def summarise(tables: dict[str, pa.Table], skillmap_shas: set[str]) -> dict:
    occ, content, repo = tables["occurrence"], tables["content"], tables["repo"]
    distinct = set(_non_empty(occ.column("blob_sha").to_pylist()))
    permissive = {_norm_repo(r) for r, ok in zip(repo.column("repo_full_name").to_pylist(),
                                                 repo.column("license_permits_text").to_pylist()) if ok}
    rep_repos = [_norm_repo(r) for r in content.column("representative_repo").to_pylist()]
    return {
        "occurrences": occ.num_rows,
        "distinct_blob_shas": len(distinct),
        "content_rows": content.num_rows,
        "repos": repo.num_rows,
        "repos_with_permissive_license": len(permissive),
        "contents_whose_representative_repo_permits_text": sum(r in permissive for r in rep_repos),
        "contents_with_commit_history": int(pc.sum(pc.equal(content.column("history_fetched"), 1)).as_py() or 0),
        "platform_folder": _counts(occ, "platform_folder"),
        "location_class": _counts(occ, "location_class"),
        "skillmap_snapshot_blob_shas": len(skillmap_shas),
        "skillmap_blob_shas_found_in_gitskills": len(skillmap_shas & distinct),
    }


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _concat(tables: list[pa.Table]) -> pa.Table:
    """Concatenate shards whose types differ slightly (e.g. an all-null column)."""
    return pa.concat_tables(tables, promote_options="permissive")


def read_local(data_dir: Path, config: str, columns: list[str]) -> tuple[pa.Table, list[dict]]:
    files = sorted(Path(data_dir, config).glob("*.parquet"))
    if not files:
        raise SystemExit(f"no parquet files under {data_dir}/{config}")
    tables = [pq.read_table(f, columns=columns) for f in files]
    inputs = [{"path": f"data/{config}/{f.name}", "bytes": f.stat().st_size, "sha256": _sha256(f)} for f in files]
    return _concat(tables), inputs


def resolve_revision(repo_id: str, revision: str):
    """Resolve the pinned revision; refuse anything that is not that commit."""
    from huggingface_hub import HfApi

    info = HfApi().dataset_info(repo_id, revision=revision, files_metadata=True)
    if not info.sha or not info.sha.startswith(revision):
        raise SystemExit(f"revision {revision} resolved to {info.sha}; refusing to continue")
    return info


def read_remote(repo_id: str, info, config: str, columns: list[str]) -> tuple[pa.Table, list[dict]]:
    """Read only the selected columns, using HTTP range requests per column chunk."""
    from huggingface_hub import HfFileSystem

    full = info.sha
    prefix = f"data/{config}/"
    siblings = sorted((s for s in info.siblings if s.rfilename.startswith(prefix)
                       and s.rfilename.endswith(".parquet")), key=lambda s: s.rfilename)
    fs = HfFileSystem()
    tables, inputs = [], []
    for s in siblings:
        with fs.open(f"datasets/{repo_id}@{full}/{s.rfilename}", "rb") as fh:
            tables.append(pq.ParquetFile(fh).read(columns=columns))
        inputs.append({"path": s.rfilename, "bytes": s.size,
                       "sha256": getattr(s.lfs, "sha256", None) if s.lfs else None})
    if not tables:
        raise SystemExit(f"no parquet files under {prefix} at {full}")
    return _concat(tables), inputs


def run(out: Path, local: Path | None = None, check_counts: bool = True,
        skillmap_root: Path = REPO_ROOT) -> dict:
    src = json.loads(SOURCES.read_text())["gitskills"]
    if local:
        artifacts, a_in = read_local(local, "artifacts", ARTIFACT_COLUMNS)
        repos, r_in = read_local(local, "repos", REPO_COLUMNS)
        # Never record this machine's absolute path in a committed manifest;
        # the input file hashes identify the data.
        revision = "local"
    else:
        info = resolve_revision(src["hf_repo"], src["hf_revision"])
        artifacts, a_in = read_remote(src["hf_repo"], info, "artifacts", ARTIFACT_COLUMNS)
        repos, r_in = read_remote(src["hf_repo"], info, "repos", REPO_COLUMNS)
        revision = info.sha

    if check_counts:
        for name, table in (("artifacts", artifacts), ("repos", repos)):
            want = src["expected_rows"][name]
            if table.num_rows != want:
                raise SystemExit(f"{name}: {table.num_rows} rows, expected {want}")

    source = f"gitskills@{revision}"
    tables = build_tables(artifacts, repos, source)
    out.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for name, table in tables.items():
        path = out / f"{name}.parquet"
        pq.write_table(table, path, compression="zstd")
        outputs[name] = {"file": path.name, "rows": table.num_rows, "sha256": _sha256(path)}

    manifest = {
        "method_version": METHOD_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source": {
            "dataset": src["hf_repo"], "revision": revision, "doi": src["zenodo_doi"],
            "license": src["license"], "paper": src["paper"],
        },
        "columns_read": {"artifacts": ARTIFACT_COLUMNS, "repos": REPO_COLUMNS},
        "inputs": {"artifacts": a_in, "repos": r_in},
        "outputs": outputs,
        "summary": summarise(tables, skillmap_blob_shas(skillmap_root)),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--local", type=Path, help="directory holding artifacts/ and repos/ parquet folders")
    ap.add_argument("--no-count-check", action="store_true", help="skip the expected row-count check")
    args = ap.parse_args(argv)
    manifest = run(args.out, args.local, check_counts=not args.no_count_check)
    json.dump(manifest["summary"], sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
