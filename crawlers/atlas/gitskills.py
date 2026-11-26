"""Import GitSkills metadata as the Atlas base catalogue.

Reads only the metadata columns of the pinned GitSkills release (never the
`content` text or commit messages) and writes three lowest-grain tables:

- occurrence: one row per SKILL.md occurrence (repo, path, blob SHA, ...)
- content:    one row per distinct blob SHA, from the GitSkills representative
- repo:       one row per repository

Policy applied on the way (DATA-POLICY.md):

- repositories on the removal list (data/exclusions.json) are dropped, and
  texts on it keep only their pointer;
- a description excerpt is published only when the licence of the earliest
  copy of that text is on the allow-list (crawlers/licensing.py); otherwise the
  row carries the pointer and says why the description was withheld;
- every table carries CC BY 4.0 attribution in its Parquet metadata.

Each remote data file's selected columns are saved under OUT/.cache as they
arrive, so an interrupted run resumes without downloading them again.

Parquet outputs are kept out of git (see data/atlas/.gitignore). The small
manifest.json, with the resolved revision, input file hashes, row counts and
output hashes, is meant to be committed after a run so every later step can
cite exactly what it used.

Usage:
    python -m crawlers.atlas.gitskills                  # remote, pinned revision
    python -m crawlers.atlas.gitskills --local DIR      # a local copy of data/
    python -m crawlers.atlas.gitskills --no-cache       # ignore saved columns
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

from crawlers import exclusions as removal
from crawlers import licensing

METHOD_VERSION = "gitskills-import/1.2.1"
REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES = Path(__file__).with_name("sources.json")
DEFAULT_OUT = REPO_ROOT / "data" / "atlas" / "gitskills"
DEFAULT_EXCLUSIONS = REPO_ROOT / "data" / "exclusions.json"

# Written into every output table's Parquet metadata and into the manifest.
ATTRIBUTION = {
    "license": "CC-BY-4.0",
    "attribution": (
        "Skill Map annotations by Dave Holmes-Kinsella and contributors "
        "(https://github.com/dhk/skill-map), CC BY 4.0. Built from GitSkills by "
        "Destefanis, Graziotin, Vaccargiu and Ortu "
        "(https://doi.org/10.5281/zenodo.21875637), CC BY 4.0."
    ),
    "license_note": (
        "Description excerpts are not covered by CC BY 4.0; they stay under "
        "their authors' terms. See DATA-POLICY.md and LICENSE-DATA.md."
    ),
}

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

def license_permits_text(license_id: str | None) -> bool:
    """Is this repository licence on the DATA-POLICY.md allow-list?"""
    return licensing.normalise(license_id) is not None


def _norm_repo(name: str | None) -> str:
    return (name or "").strip().lower()


def _non_empty(values) -> list:
    return [v for v in values if v not in (None, "")]

EXCERPT_LIMIT = licensing.EXCERPT_MAX_CHARS  # characters, per DATA-POLICY.md


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


def _sortable(v) -> str | None:
    if v in (None, ""):
        return None
    return v.isoformat() if hasattr(v, "isoformat") else str(v)


def _ensure_representatives(artifacts: pa.Table) -> tuple[pa.Table, int]:
    """Give every blob SHA exactly one representative row, promoting the first
    remaining occurrence where an earlier step removed the representative."""
    shas = artifacts.column("file_sha").to_pylist()
    primary = artifacts.column("dedup_primary").to_pylist()
    has_primary = {s for s, p in zip(shas, primary) if p == 1}
    reassigned = 0
    for i, s in enumerate(shas):
        if s and s not in has_primary:
            primary[i] = 1
            has_primary.add(s)
            reassigned += 1
    if reassigned:
        idx = artifacts.schema.get_field_index("dedup_primary")
        artifacts = artifacts.set_column(
            idx, "dedup_primary", pa.array(primary, artifacts.schema.field("dedup_primary").type))
    return artifacts, reassigned


def reconcile_duplicates(artifacts: pa.Table, repos: pa.Table) -> tuple[pa.Table, pa.Table, dict]:
    """Merge repositories whose names differ only by case, and their occurrences.

    GitHub treats owner/name case-insensitively, so two GitSkills rows such as
    `Foo/Bar` and `foo/bar` are one repository seen under two spellings (a
    rename or a case change between crawls). One row is kept per name, chosen
    deterministically: the latest `pushed_at` (the spelling GitHub reported
    most recently), then the most stars, then the spelling that sorts first.
    Occurrences under any spelling are re-keyed to the kept one. If that makes
    two occurrences share a repo and path, the representative row is kept,
    then the latest `discovered_at`, then the first in input order.

    Nothing is dropped silently: the returned report lists every merged
    repository and counts every merged occurrence, and goes in the manifest.
    """
    names = repos.column("full_name").to_pylist()
    groups: dict[str, list[int]] = {}
    for i, n in enumerate(names):
        groups.setdefault(_norm_repo(n), []).append(i)
    dupes = {k: v for k, v in groups.items() if len(v) > 1}
    report = {"rule": ("keep latest pushed_at, then most stars, then first spelling; "
                       "re-key occurrences; on repo+path collision keep the representative, "
                       "then latest discovered_at"),
              "repos_merged": [], "repo_rows_dropped": 0,
              "occurrences_merged": 0, "texts_dropped": 0, "occurrence_examples": [],
              "representatives_reassigned": 0}
    if not dupes:
        return artifacts, repos, report

    pushed = repos.column("pushed_at").to_pylist()
    stars = repos.column("stars").to_pylist()
    keep_rows = set(range(repos.num_rows))
    canonical: dict[str, str] = {}
    for key, rows in sorted(dupes.items()):
        # max() keeps the first of equal candidates, so sorting by spelling
        # first makes the final tie-break "spelling that sorts first".
        by_name = sorted(rows, key=lambda i: names[i])
        best = max(by_name, key=lambda i: (_sortable(pushed[i]) is not None,
                                           _sortable(pushed[i]) or "",
                                           stars[i] or 0))
        canonical[key] = names[best]
        dropped = [names[i] for i in rows if i != best]
        keep_rows -= set(rows) - {best}
        report["repos_merged"].append({"kept": names[best], "merged": dropped})
        report["repo_rows_dropped"] += len(dropped)
    repos = repos.take(pa.array(sorted(keep_rows)))

    occ_repos = artifacts.column("repo_full_name").to_pylist()
    rekeyed = [canonical.get(_norm_repo(r), r) for r in occ_repos]
    paths = artifacts.column("path").to_pylist()
    primary = artifacts.column("dedup_primary").to_pylist()
    found = artifacts.column("discovered_at").to_pylist()
    winner: dict[tuple, int] = {}
    losers: list[tuple[int, int]] = []  # (dropped row, kept row)
    for i, (r, p) in enumerate(zip(rekeyed, paths)):
        k = (_norm_repo(r), p)
        if k not in winner:
            winner[k] = i
            continue
        j = winner[k]
        rank_i = (primary[i] == 1, _sortable(found[i]) or "")
        rank_j = (primary[j] == 1, _sortable(found[j]) or "")
        loser = j if rank_i > rank_j else i
        if loser == j:
            winner[k] = i
        losers.append((loser, i if loser == j else j))
    keep_occ = sorted(winner.values())
    all_shas = artifacts.column("file_sha").to_pylist()
    kept_shas = {all_shas[i] for i in keep_occ}
    report["occurrences_merged"] = len(losers)
    for loser, kept in losers:
        lost = all_shas[loser] not in kept_shas
        report["texts_dropped"] += int(lost)
        if len(report["occurrence_examples"]) < 50:
            report["occurrence_examples"].append({
                "repo": rekeyed[kept], "path": paths[kept],
                "dropped_row_spelling": occ_repos[loser], "kept_row_spelling": occ_repos[kept],
                "dropped_sha": all_shas[loser], "kept_sha": all_shas[kept],
                "dropped_text_kept_elsewhere": not lost,
            })
    idx = artifacts.schema.get_field_index("repo_full_name")
    artifacts = artifacts.set_column(idx, "repo_full_name", pa.array(rekeyed, pa.string()))
    artifacts = artifacts.take(pa.array(keep_occ))
    # A dropped duplicate may have been a text's representative, or a text may
    # now have two; keep exactly one, preferring the earliest kept row.
    shas = artifacts.column("file_sha").to_pylist()
    prim = artifacts.column("dedup_primary").to_pylist()
    seen: set = set()
    for i, (sha, pr) in enumerate(zip(shas, prim)):
        if pr == 1:
            if sha in seen:
                prim[i] = 0
            seen.add(sha)
    pidx = artifacts.schema.get_field_index("dedup_primary")
    artifacts = artifacts.set_column(pidx, "dedup_primary",
                                     pa.array(prim, artifacts.schema.field("dedup_primary").type))
    artifacts, report["representatives_reassigned"] = _ensure_representatives(artifacts)
    return artifacts, repos, report


def apply_exclusions(artifacts: pa.Table, repos: pa.Table,
                     ex: removal.Exclusions) -> tuple[pa.Table, pa.Table, dict]:
    """Drop repositories on the removal list. Where that removes a text's
    representative row, the first remaining occurrence becomes the
    representative, so the text keeps exactly one content row."""
    occ_keep = pa.array([not ex.repo_excluded(r) for r in artifacts.column("repo_full_name").to_pylist()])
    repo_keep = pa.array([not ex.repo_excluded(r) for r in repos.column("full_name").to_pylist()])
    kept = artifacts.filter(occ_keep)
    stats = {
        "repos_excluded": repos.num_rows - int(pc.sum(repo_keep).as_py() or 0),
        "occurrences_dropped": artifacts.num_rows - kept.num_rows,
        "representatives_reassigned": 0,
    }
    if stats["occurrences_dropped"]:
        kept, stats["representatives_reassigned"] = _ensure_representatives(kept)
    return kept, repos.filter(repo_keep), stats


def earliest_copy_licence(artifacts: pa.Table, repos: pa.Table) -> dict[str, tuple[str | None, str]]:
    """For each blob SHA, the licence of the repository holding its earliest copy.

    Earliest means the earliest git first-commit date among the copies that
    have one. When no copy has a commit date, it falls back to the copy whose
    repository was created first. Ties go to the repository name, so the
    choice is deterministic. Returns {blob_sha: (licence, repo)}.
    """
    lic = {}
    created = {}
    for name, l, c in zip(repos.column("full_name").to_pylist(),
                          repos.column("license").to_pylist(),
                          repos.column("created_at").to_pylist()):
        lic[_norm_repo(name)] = l
        created[_norm_repo(name)] = _sortable(c)
    best: dict[str, tuple] = {}
    for repo, sha, first in zip(artifacts.column("repo_full_name").to_pylist(),
                                artifacts.column("file_sha").to_pylist(),
                                artifacts.column("first_commit_at").to_pylist()):
        if not sha:
            continue
        r = _norm_repo(repo)
        first = _sortable(first)
        key = (0, first, r) if first else (1, created.get(r) or "9999", r)
        if sha not in best or key < best[sha][0]:
            best[sha] = (key, repo)
    return {sha: (lic.get(_norm_repo(repo)), repo) for sha, (_, repo) in best.items()}


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


def build_tables(artifacts: pa.Table, repos: pa.Table, source: str,
                 ex: removal.Exclusions | None = None,
                 report: dict | None = None) -> dict[str, pa.Table]:
    """Turn GitSkills artifacts and repos into occurrence, content and repo tables.

    If `report` is given, it is filled with what was merged and removed."""
    ex = ex or removal.Exclusions(set(), set())
    artifacts, repos, dup_report = reconcile_duplicates(artifacts, repos)
    artifacts, repos, removal_stats = apply_exclusions(artifacts, repos, ex)
    if report is not None:
        report["duplicates"] = dup_report
        report["removal"] = removal_stats
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
    earliest = earliest_copy_licence(artifacts, repos)
    rep_shas = reps.column("file_sha").to_pylist()
    content_lic = [earliest.get(s, (None, None)) for s in rep_shas]
    withheld = []
    for sha, (l, _) in zip(rep_shas, content_lic):
        if ex.blob_excluded(sha):
            withheld.append("removal-list")
        elif not license_permits_text(l):
            withheld.append("licence")
        else:
            withheld.append(None)
    raw_desc = reps.column("description").to_pylist()
    names = reps.column("name").to_pylist()
    description, truncated = _truncate(pa.array(
        [d if w is None else None for d, w in zip(raw_desc, withheld)], pa.string()))
    content = pa.table({
        "blob_sha": reps.column("file_sha"),
        "representative_repo": reps.column("repo_full_name"),
        "representative_path": reps.column("path"),
        "name": pa.array([n if w != "removal-list" else None for n, w in zip(names, withheld)], pa.string()),
        "description_excerpt": description,
        "description_truncated": truncated,
        "description_withheld": pa.array(withheld, pa.string()),
        "content_license": pa.array([l for l, _ in content_lic], pa.string()),
        "content_license_spdx": pa.array([licensing.normalise(l) for l, _ in content_lic], pa.string()),
        "license_from_repo": pa.array([r for _, r in content_lic], pa.string()),
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
    meta = {k.encode(): v.encode() for k, v in ATTRIBUTION.items()}
    meta[b"method_version"] = METHOD_VERSION.encode()
    meta[b"source"] = source.encode()
    return {name: t.replace_schema_metadata(meta)
            for name, t in (("occurrence", occurrence), ("content", content), ("repo", repo))}


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
    withheld = content.column("description_withheld").to_pylist()
    return {
        "occurrences": occ.num_rows,
        "distinct_blob_shas": len(distinct),
        "content_rows": content.num_rows,
        "repos": repo.num_rows,
        "repos_with_permissive_license": len(permissive),
        "contents_whose_representative_repo_permits_text": sum(r in permissive for r in rep_repos),
        "descriptions_published": sum(w is None for w in withheld),
        "descriptions_withheld_licence": sum(w == "licence" for w in withheld),
        "descriptions_withheld_removal_list": sum(w == "removal-list" for w in withheld),
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


def _cache_paths(cache_dir: Path, rfilename: str) -> tuple[Path, Path]:
    base = cache_dir / rfilename
    return base, base.with_name(base.name + ".json")


def _cache_key(revision: str, s, columns: list[str]) -> dict:
    return {"revision": revision, "path": s.rfilename, "bytes": s.size,
            "sha256": getattr(s.lfs, "sha256", None) if s.lfs else None,
            "columns": list(columns)}


def read_remote(repo_id: str, info, config: str, columns: list[str],
                cache_dir: Path | None = None) -> tuple[pa.Table, list[dict]]:
    """Read only the selected columns, using HTTP range requests per column chunk.

    With cache_dir, each data file's columns are saved as soon as they are read
    and reused on the next run if the revision, file size, file hash and column
    list all match, so a run that fails part way resumes where it stopped."""
    from huggingface_hub import HfFileSystem

    full = info.sha
    prefix = f"data/{config}/"
    siblings = sorted((s for s in info.siblings if s.rfilename.startswith(prefix)
                       and s.rfilename.endswith(".parquet")), key=lambda s: s.rfilename)
    fs = HfFileSystem()
    tables, inputs = [], []
    for s in siblings:
        key = _cache_key(full, s, columns)
        cached = None
        if cache_dir is not None:
            data_path, key_path = _cache_paths(cache_dir, s.rfilename)
            if data_path.exists() and key_path.exists() and json.loads(key_path.read_text()) == key:
                cached = pq.read_table(data_path)
        if cached is None:
            with fs.open(f"datasets/{repo_id}@{full}/{s.rfilename}", "rb") as fh:
                cached = pq.ParquetFile(fh).read(columns=columns)
            if cache_dir is not None:
                data_path.parent.mkdir(parents=True, exist_ok=True)
                tmp = data_path.with_name(data_path.name + ".tmp")
                pq.write_table(cached, tmp)
                os.replace(tmp, data_path)
                key_path.write_text(json.dumps(key))
        tables.append(cached)
        inputs.append({"path": s.rfilename, "bytes": s.size, "sha256": key["sha256"]})
    if not tables:
        raise SystemExit(f"no parquet files under {prefix} at {full}")
    return _concat(tables), inputs


def run(out: Path, local: Path | None = None, check_counts: bool = True,
        skillmap_root: Path = REPO_ROOT, exclusions_path: Path = DEFAULT_EXCLUSIONS,
        use_cache: bool = True) -> dict:
    src = json.loads(SOURCES.read_text())["gitskills"]
    # The removal list is required: a run must never publish without it.
    ex = removal.load(exclusions_path)
    cache_dir = out / ".cache" if use_cache else None
    if local:
        artifacts, a_in = read_local(local, "artifacts", ARTIFACT_COLUMNS)
        repos, r_in = read_local(local, "repos", REPO_COLUMNS)
        # Never record this machine's absolute path in a committed manifest;
        # the input file hashes identify the data.
        revision = "local"
    else:
        info = resolve_revision(src["hf_repo"], src["hf_revision"])
        artifacts, a_in = read_remote(src["hf_repo"], info, "artifacts", ARTIFACT_COLUMNS, cache_dir)
        repos, r_in = read_remote(src["hf_repo"], info, "repos", REPO_COLUMNS, cache_dir)
        revision = info.sha

    if check_counts:
        for name, table in (("artifacts", artifacts), ("repos", repos)):
            want = src["expected_rows"][name]
            if table.num_rows != want:
                raise SystemExit(f"{name}: {table.num_rows} rows, expected {want}")

    source = f"gitskills@{revision}"
    report: dict = {}
    tables = build_tables(artifacts, repos, source, ex, report)
    removal_stats = report["removal"]
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
        "attribution": ATTRIBUTION,
        "removal_list": {
            "path": "data/exclusions.json",
            "sha256": _sha256(Path(exclusions_path)),
            **removal_stats,
        },
        "duplicate_repo_names": report["duplicates"],
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
    ap.add_argument("--no-cache", action="store_true", help="read every remote file again, ignoring saved columns")
    args = ap.parse_args(argv)
    manifest = run(args.out, args.local, check_counts=not args.no_count_check,
                   use_cache=not args.no_cache)
    json.dump(manifest["summary"], sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
