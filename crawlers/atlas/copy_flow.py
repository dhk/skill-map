"""Export how vendor skills are copied into other repositories, for the copy-flow diagrams.

Reads the vendor reference outputs (crawlers/atlas/vendor_reference.py), which
must include mirror.parquet (built with --gitskills), and writes one
aggregated, pointer-only JSON file for atlas-copies.html:

- vendors:      per vendor, skills published, skills copied, copies, copying repos;
- skills:       every vendor skill with at least one copy, with its copies and
                copying repos by agent platform folder;
- repos:        the repositories that copy the most distinct vendor skills;
- edges:        skill -> repo copy counts, for those repositories only;
- cross_vendor: copies from one vendor's repository into another's.

A "skill" is a vendor repository and SKILL.md path; a copy is a GitSkills
occurrence outside the vendor repositories whose text is byte-identical to one
of that skill's versions. No skill text is read or written. Repositories on
the removal list (data/exclusions.json) are dropped, and skills whose text is
on it are flagged.

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

METHOD_VERSION = "copy-flow/1.0.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IN = REPO_ROOT / "data" / "atlas" / "vendor_reference"
DEFAULT_OUT = DEFAULT_IN / "copy_flow.json"
DEFAULT_EXCLUSIONS = REPO_ROOT / "data" / "exclusions.json"
PLATFORMS = ["claude", "agents", "codex", "cursor", "github", "opencode",
             "gemini", "kiro", "windsurf", "other"]

ATTRIBUTION = (
    "Skill Map copy-flow data by Dave Holmes-Kinsella and contributors "
    "(https://github.com/dhk/skill-map), CC BY 4.0. Built from vendors' public "
    "repositories and GitSkills (Destefanis, Graziotin, Vaccargiu and Ortu, "
    "doi:10.5281/zenodo.21875637), CC BY 4.0. Pointers only; no file text."
)


def skill_id(repo: str, path: str) -> str:
    return f"{repo}:{path}"


def skill_name(path: str) -> str:
    parent = PurePosixPath(path).parent.name
    return parent or PurePosixPath(path).name


def build(versions: list[dict], skills: list[dict], mirror: list[dict], cross: list[dict],
          ex: removal.Exclusions, max_repos: int = 500, min_skills: int = 3) -> dict:
    listed = {(v["repo"], v["path"]) for v in versions if v.get("removal_listed")}
    info = {(s["repo"], s["path"]): s for s in skills}

    per_skill: dict[str, dict] = {}
    repo_skills: dict[str, Counter] = defaultdict(Counter)
    repo_vendors: dict[str, Counter] = defaultdict(Counter)
    dropped = 0
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
                "removal_listed": (m["vendor_repo"], m["vendor_path"]) in listed,
                "_versions_copied": set(), "_repos": set(),
                "_platform_copies": Counter(), "_platform_repos": defaultdict(set),
                "copies": 0,
            }
        folder = m.get("copy_platform_folder") or "other"
        if folder not in PLATFORMS:
            folder = "other"
        repo = m["copy_repo"]
        s["copies"] += 1
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

    ranked = sorted(repo_skills.items(), key=lambda kv: (-len(kv[1]), -sum(kv[1].values()), kv[0]))
    top = [(r, c) for r, c in ranked if len(c) >= min_skills][:max_repos]
    repos_out = [{"repo": r, "skills": len(c), "copies": sum(c.values()),
                  "vendors": dict(sorted(repo_vendors[r].items()))} for r, c in top]
    edges = [{"skill": sid, "repo": r, "copies": n}
             for r, c in top for sid, n in sorted(c.items())]

    cross_out = [{
        "origin_vendor": c["origin_vendor"], "origin_skill": skill_id(c["origin_repo"], c["origin_path"]),
        "origin_landed_at": c["origin_landed_at"], "copy_vendor": c["copy_vendor"],
        "copy_repo": c["copy_repo"], "copy_path": c["copy_path"],
        "copy_landed_at": c["copy_landed_at"], "copy_authorship": c["copy_authorship"],
        "same_day": bool(c["same_day"]),
    } for c in cross]

    return {
        "vendors": vendors, "skills": out_skills, "repos": repos_out,
        "edges": edges, "cross_vendor": cross_out,
        "totals": {
            "copies": sum(s["copies"] for s in out_skills),
            "copy_repos": len({r.lower() for r in repo_skills}),
            "skills_copied": len(out_skills),
            "skills_published": len(skills),
            "copies_dropped_removal_list": dropped,
            "repos_shown": len(repos_out), "min_skills_for_repo": min_skills,
        },
    }


def run(src: Path = DEFAULT_IN, out: Path = DEFAULT_OUT,
        exclusions_path: Path = DEFAULT_EXCLUSIONS, max_repos: int = 500,
        min_skills: int = 3) -> dict:
    mirror_path = src / "mirror.parquet"
    if not mirror_path.exists():
        raise FileNotFoundError(
            f"{mirror_path} is missing: run "
            "`python -m crawlers.atlas.vendor_reference --gitskills data/atlas/gitskills` first")
    read = lambda name: pq.read_table(src / name).to_pylist()  # noqa: E731
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    data = build(read("version.parquet"), read("skill.parquet"), read("mirror.parquet"),
                 read("cross_vendor.parquet"), removal.load(exclusions_path),
                 max_repos=max_repos, min_skills=min_skills)
    data["meta"] = {
        "method_version": METHOD_VERSION,
        "built_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "attribution": ATTRIBUTION,
        "vendor_reference": {"method_version": manifest.get("method_version"),
                             "built_at": manifest.get("built_at"),
                             "outputs": manifest.get("outputs")},
        "gitskills_revision": (manifest.get("mirror") or {}).get("gitskills_revision"),
        "removal_list_sha256": hashlib.sha256(Path(exclusions_path).read_bytes()).hexdigest(),
        "platforms": PLATFORMS,
    }
    out.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--exclusions", type=Path, default=DEFAULT_EXCLUSIONS)
    ap.add_argument("--max-repos", type=int, default=500)
    ap.add_argument("--min-skills", type=int, default=3)
    args = ap.parse_args(argv)
    data = run(args.src, args.out, args.exclusions, args.max_repos, args.min_skills)
    print(json.dumps(data["totals"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
