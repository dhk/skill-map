"""Export how vendor skills are copied into other repositories, for the copy-flow diagrams.

Reads the vendor reference outputs (crawlers/atlas/vendor_reference.py), which
must include mirror.parquet (built with --gitskills), and writes one
aggregated, pointer-only JSON file for atlas-copies.html:

- vendors:      per vendor, skills published, skills copied, copies, copying repos;
- skills:       the vendor skills found in the most repositories (--max-skills),
                with their files and repositories by agent platform folder;
- skills_rest:  every other copied skill, summed per vendor;
- repos:        the repositories that hold the most distinct vendor skills;
- edges:        [skill index, repo index, files] for those skills and repositories;
- cross_vendor: copies from one vendor's repository into another's.

A "skill" is a vendor repository and SKILL.md path; a copy is a GitSkills
occurrence outside the vendor repositories whose text is byte-identical to one
of that skill's versions. Each text is credited only to the earliest vendor
path that published it, so a skill that was moved or republished elsewhere can
show no copies. No skill text is read or written. Repositories on the removal
list (data/exclusions.json) are dropped, and each copy whose text is on it is
counted per skill.

The inputs must match the hashes in the vendor reference manifest, and the
manifest must have a mirror section, so a mirror.parquet left over from an
older run is refused. If the output is over MAX_BYTES the skill and repository
caps step down (FIT_STEPS) until it fits; if it still doesn't, it is written
under release/ for a GitHub release asset instead (ADR 0007). The full grain
stays in mirror.parquet.

Usage:
    python -m crawlers.atlas.copy_flow
    python -m crawlers.atlas.copy_flow --max-repos 400 --min-skills 3
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

import pyarrow.parquet as pq

from crawlers import exclusions as removal

METHOD_VERSION = "copy-flow/1.2.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = REPO_ROOT / "data" / "atlas" / "vendor_reference"
DEFAULT_OUT = DEFAULT_IN / "copy_flow.json"
DEFAULT_EXCLUSIONS = REPO_ROOT / "data" / "exclusions.json"
INPUTS = ("version.parquet", "skill.parquet", "mirror.parquet", "cross_vendor.parquet")
MAX_BYTES = 1_000_000
MAX_REPOS, MAX_SKILLS = 500, 400
# (max_repos, max_skills) tried in order when the output is over MAX_BYTES.
FIT_STEPS = ((300, 300), (200, 300), (150, 200), (100, 150))
PLATFORMS = ["claude", "agents", "codex", "cursor", "github", "opencode",
             "gemini", "kiro", "windsurf", "other"]

ATTRIBUTION = (
    "Skill Map copy-flow data by Dave Holmes-Kinsella and contributors "
    "(https://github.com/dhk/skill-map), CC BY 4.0. Built from vendors' public "
    "repositories and GitSkills (Destefanis, Graziotin, Vaccargiu and Ortu, "
    "doi:10.5281/zenodo.21875637), CC BY 4.0. Pointers only; no file text."
)


class StaleInputError(RuntimeError):
    """The vendor reference outputs on disk don't match their manifest."""


def skill_id(repo: str, path: str) -> str:
    return f"{repo}:{path}"


def skill_name(path: str) -> str:
    parent = PurePosixPath(path).parent.name
    return parent or PurePosixPath(path).name


def build(versions: list[dict], skills: list[dict], mirror: list[dict], cross: list[dict],
          ex: removal.Exclusions, max_repos: int = MAX_REPOS, min_skills: int = 3,
          max_skills: int = MAX_SKILLS) -> dict:
    info = {(s["repo"], s["path"]): s for s in skills}

    per_skill: dict[str, dict] = {}
    repo_skills: dict[str, Counter] = defaultdict(Counter)
    repo_vendors: dict[str, Counter] = defaultdict(Counter)
    dropped = listed_copies = 0
    for m in mirror:
        if ex.repo_excluded(m["copy_repo"]):
            dropped += 1
            continue
        sid = skill_id(m["vendor_repo"], m["vendor_path"])
        s = per_skill.get(sid)
        if s is None:
            meta = info.get((m["vendor_repo"], m["vendor_path"]), {})
            s = per_skill[sid] = {
                "id": sid, "vendor": m["vendor"], "repo": m["vendor_repo"],
                "path": m["vendor_path"], "name": skill_name(m["vendor_path"]),
                "authorship": meta.get("authorship"),
                "manifest_author": meta.get("manifest_author"),
                "versions": meta.get("versions"),
                "first_landed_at": meta.get("first_landed_at"),
                "present_at_head": meta.get("present_at_head"),
                "removal_listed_copies": 0,
                "_versions_copied": set(), "_repos": set(),
                "_platform_copies": Counter(), "_platform_repos": defaultdict(set),
                "copies": 0,
            }
        folder = m.get("copy_platform_folder") or "other"
        if folder not in PLATFORMS:
            folder = "other"
        repo = m["copy_repo"]
        s["copies"] += 1
        if ex.blob_excluded(m["blob_sha"]):
            s["removal_listed_copies"] += 1
            listed_copies += 1
        s["_versions_copied"].add(m["blob_sha"])
        s["_repos"].add(repo.lower())
        s["_platform_copies"][folder] += 1
        s["_platform_repos"][folder].add(repo.lower())
        repo_skills[repo][sid] += 1
        repo_vendors[repo][m["vendor"]] += 1

    out_skills = []
    for s in per_skill.values():
        s["versions_copied"] = len(s.pop("_versions_copied"))
        s["copy_repos"] = len(s.pop("_repos"))
        pc, pr = s.pop("_platform_copies"), s.pop("_platform_repos")
        s["by_platform"] = {p: {"copies": pc[p], "repos": len(pr[p])} for p in PLATFORMS if pc[p]}
        out_skills.append(s)
    out_skills.sort(key=lambda s: (-s["copy_repos"], -s["copies"], s["id"]))

    published = Counter(s["vendor"] for s in skills)
    vendors = []
    for vendor in sorted(published):
        mine = [s for s in out_skills if s["vendor"] == vendor]
        repos = {r for r, vs in repo_vendors.items() if vs.get(vendor)}
        vendors.append({
            "vendor": vendor, "skills_published": published[vendor],
            "skills_copied": len(mine), "copies": sum(s["copies"] for s in mine),
            "copy_repos": len({r.lower() for r in repos}),
        })
    vendors.sort(key=lambda v: (-v["copy_repos"], v["vendor"]))

    shown, tail = out_skills[:max_skills], out_skills[max_skills:]
    rest: dict[str, dict] = {}
    for t in tail:
        r = rest.setdefault(t["vendor"], {"vendor": t["vendor"], "skills": 0, "copies": 0,
                                          "removal_listed_copies": 0, "by_platform": Counter()})
        r["skills"] += 1
        r["copies"] += t["copies"]
        r["removal_listed_copies"] += t["removal_listed_copies"]
        for p, c in t["by_platform"].items():
            r["by_platform"][p] += c["copies"]
    skills_rest = [{**r, "by_platform": {p: {"copies": r["by_platform"][p]} for p in PLATFORMS
                                         if r["by_platform"][p]}}
                   for r in sorted(rest.values(), key=lambda r: r["vendor"])]

    # Repositories ranked by how many distinct vendor skills they hold (all skills count).
    ranked = sorted(repo_skills.items(), key=lambda kv: (-len(kv[1]), -sum(kv[1].values()), kv[0]))
    top = [(r, c) for r, c in ranked if len(c) >= min_skills][:max_repos]
    repos_out = [{"repo": r, "skills": len(c), "copies": sum(c.values()),
                  "vendors": dict(sorted(repo_vendors[r].items()))} for r, c in top]
    skill_index = {sk["id"]: i for i, sk in enumerate(shown)}
    edges = [[skill_index[sid], ri, n]
             for ri, (_r, c) in enumerate(top) for sid, n in sorted(c.items()) if sid in skill_index]

    cross_out = [{
        "origin_vendor": c["origin_vendor"], "origin_skill": skill_id(c["origin_repo"], c["origin_path"]),
        "origin_landed_at": c["origin_landed_at"], "copy_vendor": c["copy_vendor"],
        "copy_repo": c["copy_repo"], "copy_path": c["copy_path"],
        "copy_landed_at": c["copy_landed_at"], "copy_authorship": c["copy_authorship"],
        "same_day": bool(c["same_day"]),
    } for c in cross]

    return {
        "vendors": vendors, "skills": shown, "skills_rest": skills_rest, "repos": repos_out,
        "edges": edges, "cross_vendor": cross_out,
        "totals": {
            "copies": sum(s["copies"] for s in out_skills),
            "copy_repos": len({r.lower() for r in repo_skills}),
            "skills_copied": len(out_skills),
            "skills_published": len(skills),
            "copies_dropped_removal_list": dropped,
            "copies_of_removal_listed_texts": listed_copies,
            "skills_shown": len(shown), "repos_shown": len(repos_out),
            "min_skills_for_repo": min_skills,
        },
    }


def check_inputs(src: Path) -> tuple[dict, dict[str, str]]:
    """Load the manifest and confirm every input is the file it describes."""
    manifest_path = src / "manifest.json"
    if not (src / "mirror.parquet").exists() or not manifest_path.exists():
        raise FileNotFoundError(
            f"{src / 'mirror.parquet'} or its manifest is missing: run "
            "`python -m crawlers.atlas.vendor_reference --gitskills data/atlas/gitskills` first")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("mirror"):
        raise StaleInputError(
            "the vendor reference manifest has no mirror section, so mirror.parquet on disk "
            "is from another run: rerun vendor_reference with --gitskills")
    recorded = {o["path"]: o["sha256"] for o in manifest.get("outputs") or []}
    hashes = {}
    for name in INPUTS:
        path = src / name
        if not path.exists():
            raise FileNotFoundError(f"{path} is missing: rerun vendor_reference with --gitskills")
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        if recorded.get(name) != h:
            raise StaleInputError(
                f"{name} does not match the hash in {manifest_path.name}: rerun "
                "vendor_reference with --gitskills so the tables and manifest agree")
        hashes[name] = h
    hashes["manifest.json"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return manifest, hashes


def run(src: Path = DEFAULT_IN, out: Path = DEFAULT_OUT,
        exclusions_path: Path = DEFAULT_EXCLUSIONS, max_repos: int = MAX_REPOS,
        min_skills: int = 3, max_bytes: int = MAX_BYTES,
        max_skills: int = MAX_SKILLS) -> tuple[dict, Path]:
    """Write the export; return it and the path written (under release/ when too big)."""
    manifest, hashes = check_inputs(src)
    read = lambda name: pq.read_table(src / name).to_pylist()  # noqa: E731
    tables = [read(n) for n in ("version.parquet", "skill.parquet", "mirror.parquet",
                                "cross_vendor.parquet")]
    ex = removal.load(exclusions_path)
    steps = [(max_repos, max_skills)] + [(min(r, max_repos), min(k, max_skills))
                                         for r, k in FIT_STEPS]
    for repos_cap, skills_cap in steps:
        data = build(*tables, ex, max_repos=repos_cap, min_skills=min_skills, max_skills=skills_cap)
        data["meta"] = _meta(manifest, hashes, exclusions_path,
                             {"max_repos": repos_cap, "max_skills": skills_cap,
                              "reduced_to_fit": (repos_cap, skills_cap) != (max_repos, max_skills)})
        body = (json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        if len(body) <= max_bytes:
            break
    else:
        out = out.parent / "release" / out.name
        out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    return data, out


def _meta(manifest: dict, hashes: dict, exclusions_path: Path, caps: dict) -> dict:
    return {
        "method_version": METHOD_VERSION,
        "built_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "attribution": ATTRIBUTION,
        "credit_rule": "each text is credited to the earliest vendor path that published it",
        "vendor_reference": {"method_version": manifest.get("method_version"),
                             "built_at": manifest.get("built_at")},
        "inputs_sha256": hashes,
        "gitskills_revision": manifest["mirror"].get("gitskills_revision"),
        "removal_list_sha256": hashlib.sha256(Path(exclusions_path).read_bytes()).hexdigest(),
        "platforms": PLATFORMS,
        "caps": caps,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--exclusions", type=Path, default=DEFAULT_EXCLUSIONS)
    ap.add_argument("--max-repos", type=int, default=MAX_REPOS)
    ap.add_argument("--max-skills", type=int, default=MAX_SKILLS)
    ap.add_argument("--min-skills", type=int, default=3)
    ap.add_argument("--max-bytes", type=int, default=MAX_BYTES,
                    help="larger output goes under release/ for a release asset, not a commit")
    args = ap.parse_args(argv)
    try:
        data, written = run(args.src, args.out, args.exclusions, args.max_repos,
                            args.min_skills, args.max_bytes, args.max_skills)
    except (FileNotFoundError, StaleInputError) as e:
        print(f"copy_flow: {e}", file=sys.stderr)
        return 2
    print(json.dumps(data["totals"], indent=2))
    size = written.stat().st_size
    if written != args.out:
        print(f"copy_flow: output is {size:,} bytes, over {args.max_bytes:,}, so it was written to "
              f"{written} for a release asset. Don't commit it; lower --max-repos and --max-skills "
              "to fit, or attach it to a release (ADR 0007).", file=sys.stderr)
        return 3
    caps = data["meta"]["caps"]
    note = " (caps lowered to fit)" if caps["reduced_to_fit"] else ""
    print(f"wrote {written} ({size:,} bytes; {caps['max_skills']} skills, "
          f"{caps['max_repos']} repositories{note})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
