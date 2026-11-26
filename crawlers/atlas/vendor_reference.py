"""Build the vendor reference set: every SKILL.md version vendors have published.

The Atlas flags vendor repackaging (docs/atlas/plan.md, phase 1) by comparing
skills in the wild with what vendors ship. This module records, for each
repository in crawlers/atlas/vendors.json, every version of every SKILL.md
that landed on the default branch, as git blob SHAs. It copies no skill text:
the outputs are pointers (repository, path, commit, date, blob SHA).

How a version is found:

- each repository is cloned without file contents (`--filter=blob:none`), so
  history and paths are complete but blobs are fetched only when read;
- `git log --first-parent --diff-merges=first-parent --no-renames --raw` over
  `*SKILL.md` on the default branch lists each add, change and delete in the
  order it landed, dated by the commit that put it on the default branch (for
  a merged pull request, the merge commit), so unmerged branches never count;
- renames show as a delete and an add with the same blob SHA.

Who wrote a skill is read from the nearest plugin manifest above it
(`plugin.json` inside any `.<name>-plugin/` or `.plugin/` folder, such as
`.claude-plugin`, `.codex-plugin` or `.cursor-plugin`) at the commit that added
or changed it. A manifest that is a symlink inside the repository is followed:

- first-party:  the manifest's author matches one of the vendor's names;
- other-author: the manifest names someone else (a partner company, a team,
                or a person), or, with no author, the path sits under one of
                the repository's partner_paths;
- unstated:     no manifest author and no partner path. The vendor published
                it, but nothing says who wrote it.

authorship_basis says which of those it rests on (manifest, partner_path or
none), and manifest_author keeps the name exactly as written, so a reader can
regroup "other-author" (a team name may well be the vendor's own staff; this
module does not guess). Template placeholders such as "Your Name" count as no
author.

Outputs (in data/atlas/vendor_reference/, Parquet kept out of git like the
other Atlas tables; manifest.json is committed):

- version.parquet: one row per SKILL.md add, change or delete;
- skill.parquet:   one row per repository and skill directory;
- cross_vendor.parquet: one row per vendor version that another vendor later
                   published byte for byte (origin, copy, both landing dates);
- mirror.parquet:  with --gitskills, one row per GitSkills occurrence outside
                   the vendor repositories whose blob SHA is a vendor version
                   (an exact copy of something a vendor published);
- manifest.json:   method version, each repository's pinned HEAD, row counts,
                   output hashes.

All dates are UTC (`YYYY-MM-DDTHH:MM:SSZ`), so they sort correctly as text;
ties keep git's landing order.

The removal list (data/exclusions.json) is loaded as the GitSkills importer
loads it: repositories on it are skipped, and texts on it keep their pointer
with `removal_listed` set.

Usage:
    python -m crawlers.atlas.vendor_reference
    python -m crawlers.atlas.vendor_reference --gitskills data/atlas/gitskills
    python -m crawlers.atlas.vendor_reference --offline   # reuse clones as they are
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

import os
import re

import pyarrow as pa
import pyarrow.parquet as pq

from crawlers import exclusions as removal

METHOD_VERSION = "vendor-reference/1.1.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
VENDORS = Path(__file__).with_name("vendors.json")
DEFAULT_OUT = REPO_ROOT / "data" / "atlas" / "vendor_reference"
DEFAULT_CLONES = REPO_ROOT / "data" / "atlas" / ".cache" / "vendor-clones"
DEFAULT_EXCLUSIONS = REPO_ROOT / "data" / "exclusions.json"
NULL_SHA = "0" * 40
SKILL_FILE = "SKILL.md"
CHANGE = {"A": "added", "M": "modified", "D": "deleted", "T": "modified"}

ATTRIBUTION = {
    "license": "CC-BY-4.0",
    "attribution": (
        "Skill Map vendor reference set by Dave Holmes-Kinsella and contributors "
        "(https://github.com/dhk/skill-map). Pointers to files in each vendor's "
        "public repository; no file text is included."
    ),
}


# ---------------------------------------------------------------- config

def load_vendors(path: Path = VENDORS) -> list[dict]:
    """Flatten vendors.json into one dict per repository."""
    cfg = json.loads(path.read_text(encoding="utf-8"))
    out, seen = [], set()
    for vendor, spec in cfg["vendors"].items():
        names = spec.get("names") or [vendor]
        for r in spec["repos"]:
            repo = r["repo"]
            if repo.lower() in seen:
                raise ValueError(f"vendors.json lists {repo} twice")
            seen.add(repo.lower())
            out.append({
                "vendor": vendor,
                "names": names,
                "repo": repo,
                "license": r.get("license"),
                "partner_paths": r.get("partner_paths", []),
            })
    return out


# ---------------------------------------------------------------- git

GIT_ENV = {**os.environ, "TZ": "UTC"}


def git(repo_dir: Path, *args: str, input: str | None = None) -> str:
    res = subprocess.run(["git", "-C", str(repo_dir), *args], input=input,
                         capture_output=True, text=True, check=False, env=GIT_ENV)
    if res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])} failed in {repo_dir}: {res.stderr.strip()}")
    return res.stdout


def clone_or_update(repo: str, dest: Path, offline: bool = False) -> str:
    """Blobless clone (or fetch) of the default branch; returns the HEAD commit."""
    if not dest.exists():
        if offline:
            raise FileNotFoundError(f"--offline, but no clone of {repo} at {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout",
                        f"https://github.com/{repo}.git", str(dest)], check=True)
    elif not offline:
        git(dest, "fetch", "-q", "origin")
        git(dest, "update-ref", "HEAD", "refs/remotes/origin/HEAD")
    return git(dest, "rev-parse", "HEAD").strip()


# Dates rendered in UTC (TZ=UTC with format-local), so text order is time order.
DATE_FMT = "--date=format-local:%Y-%m-%dT%H:%M:%SZ"
LOG_FORMAT = "%x00%H%x09%cd%x09%ad"


def parse_log(text: str) -> list[dict]:
    """Parse `git log --raw --format=LOG_FORMAT` output into change rows."""
    rows = []
    for block in text.split("\x00"):
        block = block.strip("\n")
        if not block:
            continue
        head, *lines = block.split("\n")
        commit, committed_at, authored_at = head.split("\t")
        for line in lines:
            if not line.startswith(":"):
                continue
            meta, path = line.split("\t", 1)
            _old_mode, _new_mode, old_sha, new_sha, status = meta[1:].split(" ")
            status = status[0]
            if PurePosixPath(path).name != SKILL_FILE or status not in CHANGE:
                continue
            deleted = status == "D"
            rows.append({
                "commit": commit,
                "committed_at": committed_at,
                "authored_at": authored_at,
                "path": path,
                "change": CHANGE[status],
                "blob_sha": old_sha if deleted else new_sha,
                "previous_blob_sha": None if old_sha == NULL_SHA else old_sha,
            })
    return rows


def skill_changes(repo_dir: Path) -> list[dict]:
    """Every SKILL.md add, change and delete that landed on the default branch, oldest first."""
    text = git(repo_dir, "log", "--first-parent", "--diff-merges=first-parent",
               "--no-renames", "--raw", "--no-abbrev", "--reverse", DATE_FMT,
               f"--format={LOG_FORMAT}", "HEAD", "--", f"*{SKILL_FILE}")
    return parse_log(text)


# ---------------------------------------------------------------- authorship

def skill_dir(path: str) -> str:
    parent = str(PurePosixPath(path).parent)
    return "" if parent == "." else parent


def ancestor_dirs(path: str) -> list[str]:
    """Directories above a file, nearest first, ending with the root ("")."""
    parts = PurePosixPath(path).parent.parts
    return [str(PurePosixPath(*parts[:i])) if i else "" for i in range(len(parts), -1, -1)]


PLUGIN_DIR = re.compile(r"^\.(?:[A-Za-z0-9_.-]+-)?plugin$")
PLUGIN_DIR_ORDER = [".claude-plugin", ".codex-plugin", ".cursor-plugin", ".plugin"]


def plugin_dirs(entries: list[tuple[str, str]]) -> list[str]:
    """Plugin folders among a tree's (mode, name) entries, in preference order."""
    found = [name for mode, name in entries
             if mode in ("40000", "120000") and PLUGIN_DIR.match(name)]
    rank = {n: i for i, n in enumerate(PLUGIN_DIR_ORDER)}
    return sorted(found, key=lambda n: (rank.get(n, len(rank)), n))


def parse_tree(data: bytes) -> list[tuple[str, str]]:
    """(mode, name) entries of a raw git tree object."""
    out, i = [], 0
    while i < len(data):
        sp = data.index(b" ", i)
        nul = data.index(b"\0", sp)
        out.append((data[i:sp].decode(), data[sp + 1:nul].decode("utf-8", "surrogateescape")))
        i = nul + 21
    return out


def cat_batch(repo_dir: Path, names: list[str], follow_symlinks: bool = False) -> dict:
    """Read objects named like `rev:path` with one `git cat-file --batch`.

    Returns {name: (type, bytes)} for names that resolve to an object. With
    follow_symlinks, a symlink inside the repository is followed to its target;
    links that leave the tree, dangle or loop count as missing."""
    if not names:
        return {}
    args = ["git", "-C", str(repo_dir), "cat-file", "--batch"]
    if follow_symlinks:
        args.append("--follow-symlinks")
    res = subprocess.run(args, input=("\n".join(names) + "\n").encode(),
                         capture_output=True, check=False, env=GIT_ENV)
    if res.returncode != 0:
        raise RuntimeError(f"git cat-file --batch failed in {repo_dir}: {res.stderr.decode().strip()}")
    data, pos, out = res.stdout, 0, {}
    for name in names:
        nl = data.index(b"\n", pos)
        header = data[pos:nl].decode("utf-8", "surrogateescape")
        pos = nl + 1
        parts = header.split(" ")
        if header.endswith((" missing", " ambiguous")):
            continue
        if len(parts) == 2 and parts[0] in {"symlink", "dangling", "loop", "notdir"}:
            pos += int(parts[1]) + 1
            continue
        _sha, kind, size = parts[-3], parts[-2], int(parts[-1])
        out[name] = (kind, data[pos:pos + size])
        pos += size + 1
    return out


PLACEHOLDER_AUTHORS = {"your name", "author name", "author", "todo", "tbd", "name"}


def manifest_author(raw: str) -> str | None:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    author = data.get("author")
    if isinstance(author, dict):
        author = author.get("name")
    if isinstance(author, str) and author.strip():
        author = author.strip()
        return None if author.lower() in PLACEHOLDER_AUTHORS else author
    return None


def classify(author: str | None, path: str, names: list[str],
             partner_paths: list[str]) -> tuple[str, str]:
    """Return (authorship, authorship_basis) for one SKILL.md path."""
    if author:
        low = author.lower()
        first = any(n.lower() in low for n in names)
        return ("first-party" if first else "other-author"), "manifest"
    if any(path.startswith(p) for p in partner_paths):
        return "other-author", "partner_path"
    return "unstated", "none"


def _spec(rev: str, path: str) -> str:
    return f"{rev}:{path}"


def attach_authorship(rows: list[dict], repo_dir: Path, names: list[str],
                      partner_paths: list[str]) -> None:
    """Add plugin_manifest, manifest_author, authorship and its basis to each change row."""
    for r in rows:
        # A deleted file is read as it stood just before the delete.
        r["_rev"] = f"{r['commit']}^1" if r["change"] == "deleted" else r["commit"]
        r["_dirs"] = ancestor_dirs(r["path"])
    # 1. Which plugin folders sit in each directory at each revision.
    tree_specs = sorted({_spec(r["_rev"], d) for r in rows for d in r["_dirs"]})
    trees = {k: plugin_dirs(parse_tree(v[1]))
             for k, v in cat_batch(repo_dir, tree_specs).items() if v[0] == "tree"}
    # 2. Their plugin.json files, following symlinks inside the repository.
    manifest_specs = sorted({
        _spec(r["_rev"], f"{d}/{pd}/plugin.json" if d else f"{pd}/plugin.json")
        for r in rows for d in r["_dirs"] for pd in trees.get(_spec(r["_rev"], d), [])})
    blobs = {k: v[1].decode("utf-8", "replace")
             for k, v in cat_batch(repo_dir, manifest_specs, follow_symlinks=True).items()
             if v[0] == "blob"}
    for r in rows:
        hit = None
        for d in r["_dirs"]:
            for pd in trees.get(_spec(r["_rev"], d), []):
                path = f"{d}/{pd}/plugin.json" if d else f"{pd}/plugin.json"
                if _spec(r["_rev"], path) in blobs:
                    hit = path
                    break
            if hit:
                break
        r["plugin_manifest"] = hit
        r["manifest_author"] = manifest_author(blobs[_spec(r["_rev"], hit)]) if hit else None
        r["authorship"], r["authorship_basis"] = classify(
            r["manifest_author"], r["path"], names, partner_paths)
        del r["_rev"], r["_dirs"]


# ---------------------------------------------------------------- tables

VERSION_SCHEMA = pa.schema([
    ("vendor", pa.string()), ("repo", pa.string()), ("repo_license", pa.string()),
    ("path", pa.string()), ("skill_dir", pa.string()), ("commit", pa.string()),
    ("committed_at", pa.string()), ("authored_at", pa.string()), ("change", pa.string()),
    ("blob_sha", pa.string()), ("previous_blob_sha", pa.string()),
    ("plugin_manifest", pa.string()), ("manifest_author", pa.string()),
    ("authorship", pa.string()), ("authorship_basis", pa.string()),
    ("removal_listed", pa.bool_()), ("method_version", pa.string()),
])


def version_rows(repo_cfg: dict, changes: list[dict],
                 ex: removal.Exclusions | None = None) -> list[dict]:
    ex = ex or removal.Exclusions(set(), set())
    out = []
    for c in changes:
        out.append({
            "vendor": repo_cfg["vendor"], "repo": repo_cfg["repo"],
            "repo_license": repo_cfg["license"], "path": c["path"],
            "skill_dir": skill_dir(c["path"]), "commit": c["commit"],
            "committed_at": c["committed_at"], "authored_at": c["authored_at"],
            "change": c["change"], "blob_sha": c["blob_sha"],
            "previous_blob_sha": c["previous_blob_sha"],
            "plugin_manifest": c.get("plugin_manifest"),
            "manifest_author": c.get("manifest_author"),
            "authorship": c.get("authorship", "unstated"),
            "authorship_basis": c.get("authorship_basis", "none"),
            "removal_listed": ex.blob_excluded(c["blob_sha"]),
            "method_version": METHOD_VERSION,
        })
    return out


def skill_rows(versions: list[dict]) -> list[dict]:
    """One row per repository and skill directory, built from its versions in landing order."""
    groups: dict[tuple, list[dict]] = {}
    for v in versions:
        groups.setdefault((v["repo"], v["path"]), []).append(v)
    out = []
    for (repo, path), vs in sorted(groups.items()):
        vs = sorted(vs, key=lambda v: v["committed_at"])
        last = vs[-1]
        shas = [v["blob_sha"] for v in vs if v["change"] != "deleted"]
        latest_author = next((v for v in reversed(vs) if v["change"] != "deleted"), last)
        out.append({
            "vendor": last["vendor"], "repo": repo, "path": path,
            "skill_dir": last["skill_dir"],
            "skill_name": PurePosixPath(last["skill_dir"]).name or None,
            "first_landed_at": vs[0]["committed_at"],
            "last_changed_at": last["committed_at"],
            "versions": len(set(shas)),
            "present_at_head": last["change"] != "deleted",
            "head_blob_sha": None if last["change"] == "deleted" else last["blob_sha"],
            "authorship": latest_author["authorship"],
            "authorship_basis": latest_author["authorship_basis"],
            "manifest_author": latest_author["manifest_author"],
            "method_version": METHOD_VERSION,
        })
    return out


def first_landings(versions: list[dict]) -> dict[tuple[str, str], dict]:
    """The first live version of each (blob SHA, vendor), in UTC then git order."""
    first: dict[tuple[str, str], dict] = {}
    for v in sorted(versions, key=lambda v: v["committed_at"]):  # stable: ties keep git order
        if v["change"] != "deleted":
            first.setdefault((v["blob_sha"], v["vendor"]), v)
    return first


def cross_vendor_rows(versions: list[dict]) -> list[dict]:
    """One row per vendor that published, byte for byte, a text another vendor published first."""
    by_blob: dict[str, list[dict]] = {}
    for (sha, _vendor), v in first_landings(versions).items():
        by_blob.setdefault(sha, []).append(v)
    out = []
    for sha, vs in sorted(by_blob.items()):
        if len(vs) < 2:
            continue
        vs = sorted(vs, key=lambda v: v["committed_at"])
        origin = vs[0]
        for c in vs[1:]:
            out.append({
                "blob_sha": sha,
                "origin_vendor": origin["vendor"], "origin_repo": origin["repo"],
                "origin_path": origin["path"], "origin_landed_at": origin["committed_at"],
                "copy_vendor": c["vendor"], "copy_repo": c["repo"], "copy_path": c["path"],
                "copy_skill_dir": c["skill_dir"], "copy_landed_at": c["committed_at"],
                "copy_manifest_author": c["manifest_author"],
                "copy_authorship": c["authorship"],
                "same_day": origin["committed_at"][:10] == c["committed_at"][:10],
                "method_version": METHOD_VERSION,
            })
    return out


def cross_vendor_summary(rows: list[dict]) -> dict:
    pairs: dict[str, int] = {}
    for r in rows:
        k = f"{r['origin_vendor']} -> {r['copy_vendor']}"
        pairs[k] = pairs.get(k, 0) + 1
    return {
        "copies": len(rows),
        "copy_skills": len({(r["copy_repo"], r["copy_skill_dir"]) for r in rows}),
        "texts": len({r["blob_sha"] for r in rows}),
        "same_day": sum(r["same_day"] for r in rows),
        "copy_manifest_names_copier": sum(r["copy_authorship"] == "first-party" for r in rows),
        "by_pair": dict(sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def mirror_rows(versions: list[dict], occurrence: pa.Table,
                ex: removal.Exclusions | None = None) -> list[dict]:
    """GitSkills occurrences outside vendor repositories that are byte-identical to a vendor version."""
    vendor_repos = {v["repo"].lower() for v in versions}
    first: dict[str, dict] = {}
    for (sha, _vendor), v in sorted(first_landings(versions).items(),
                                    key=lambda kv: kv[1]["committed_at"]):
        first.setdefault(sha, v)
    repos = occurrence.column("repo_full_name").to_pylist()
    paths = occurrence.column("path").to_pylist()
    shas = occurrence.column("blob_sha").to_pylist()
    folders = (occurrence.column("platform_folder").to_pylist()
               if "platform_folder" in occurrence.column_names else [None] * len(shas))
    out = []
    for repo, path, sha, folder in zip(repos, paths, shas, folders):
        v = first.get(sha)
        if v is None or (repo or "").lower() in vendor_repos:
            continue
        if ex is not None and ex.repo_excluded(repo):
            continue
        out.append({
            "blob_sha": sha, "vendor": v["vendor"], "vendor_repo": v["repo"],
            "vendor_path": v["path"], "vendor_first_landed_at": v["committed_at"],
            "copy_repo": repo, "copy_path": path, "copy_platform_folder": folder,
            "method_version": METHOD_VERSION,
        })
    return out


def _table(rows: list[dict], schema: pa.Schema | None = None) -> pa.Table:
    if schema is not None:
        return pa.Table.from_pylist(rows, schema=schema)
    return pa.Table.from_pylist(rows)


def _write(table: pa.Table, path: Path, source: str) -> dict:
    meta = dict(table.schema.metadata or {})
    meta.update({b"attribution": json.dumps(ATTRIBUTION).encode(),
                 b"method_version": METHOD_VERSION.encode(), b"source": source.encode()})
    pq.write_table(table.replace_schema_metadata(meta), path)
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": path.name, "rows": table.num_rows, "sha256": h}


# ---------------------------------------------------------------- run

def summarise(versions: list[dict], skills: list[dict]) -> dict:
    by_vendor: dict[str, dict] = {}
    for s in skills:
        d = by_vendor.setdefault(s["vendor"], {"skill_paths": 0, "present_at_head": 0,
                                               "first-party": 0, "other-author": 0,
                                               "unstated": 0})
        d["skill_paths"] += 1
        d["present_at_head"] += int(s["present_at_head"])
        d[s["authorship"]] += 1
    distinct = {v["blob_sha"] for v in versions if v["change"] != "deleted"}
    return {"version_rows": len(versions), "distinct_blobs": len(distinct),
            "skill_paths": len(skills), "by_vendor": by_vendor}


def run(out: Path = DEFAULT_OUT, clones: Path = DEFAULT_CLONES, vendors_path: Path = VENDORS,
        offline: bool = False, gitskills: Path | None = None,
        exclusions_path: Path = DEFAULT_EXCLUSIONS) -> dict:
    repos = load_vendors(vendors_path)
    ex = removal.load(exclusions_path)
    out.mkdir(parents=True, exist_ok=True)
    versions, pinned, skipped = [], [], []
    for cfg in repos:
        if ex.repo_excluded(cfg["repo"]):
            skipped.append(cfg["repo"])
            continue
        dest = clones / cfg["repo"].replace("/", "__")
        head = clone_or_update(cfg["repo"], dest, offline=offline)
        changes = skill_changes(dest)
        attach_authorship(changes, dest, cfg["names"], cfg["partner_paths"])
        rows = version_rows(cfg, changes, ex)
        versions.extend(rows)
        pinned.append({"vendor": cfg["vendor"], "repo": cfg["repo"], "head": head,
                       "license": cfg["license"], "version_rows": len(rows)})
        print(f"{cfg['repo']}: {len(rows)} SKILL.md changes at {head[:12]}", file=sys.stderr)
    skills = skill_rows(versions)
    source = "vendor repositories listed in crawlers/atlas/vendors.json"
    cross = cross_vendor_rows(versions)
    outputs = [_write(_table(versions, VERSION_SCHEMA), out / "version.parquet", source),
               _write(_table(skills), out / "skill.parquet", source),
               _write(_table(cross), out / "cross_vendor.parquet", source)]
    mirror_summary = None
    if gitskills is not None:
        occ = pq.read_table(gitskills / "occurrence.parquet",
                            columns=["repo_full_name", "path", "blob_sha", "platform_folder"])
        mirrors = mirror_rows(versions, occ, ex)
        outputs.append(_write(_table(mirrors), out / "mirror.parquet",
                              "GitSkills occurrence table matched to vendor versions"))
        gm = json.loads((gitskills / "manifest.json").read_text(encoding="utf-8"))
        mirror_summary = {
            "gitskills_revision": gm.get("revision") or gm.get("source", {}).get("revision"),
            "copies": len(mirrors),
            "copy_repos": len({m["copy_repo"].lower() for m in mirrors}),
            "vendor_blobs_copied": len({m["blob_sha"] for m in mirrors}),
        }
    manifest = {
        "method_version": METHOD_VERSION,
        "built_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "attribution": ATTRIBUTION,
        "vendors_config": {"path": "crawlers/atlas/vendors.json",
                           "sha256": hashlib.sha256(vendors_path.read_bytes()).hexdigest()},
        "repos": pinned,
        "removal_list": {
            "path": "data/exclusions.json",
            "sha256": hashlib.sha256(Path(exclusions_path).read_bytes()).hexdigest(),
            "stats": {"repos_excluded": skipped,
                      "versions_removal_listed": sum(v["removal_listed"] for v in versions)},
        },
        "summary": summarise(versions, skills),
        "cross_vendor": cross_vendor_summary(cross),
        "mirror": mirror_summary,
        "outputs": outputs,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--clones", type=Path, default=DEFAULT_CLONES)
    ap.add_argument("--vendors", type=Path, default=VENDORS)
    ap.add_argument("--offline", action="store_true", help="reuse existing clones without fetching")
    ap.add_argument("--exclusions", type=Path, default=DEFAULT_EXCLUSIONS)
    ap.add_argument("--gitskills", type=Path, default=None,
                    help="GitSkills import output directory, to match exact copies")
    args = ap.parse_args(argv)
    m = run(args.out, args.clones, args.vendors, args.offline, args.gitskills, args.exclusions)
    print(json.dumps(m["summary"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
