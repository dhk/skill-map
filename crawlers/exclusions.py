"""
exclusions.py — The removal list, and applying it to the crawl snapshots.

data/exclusions.json holds two kinds of entry (DATA-POLICY.md, "Asking for
removal" and "Text already in the snapshots"):

  repos  — repositories whose authors asked to be left out. Future crawls skip
           them, and their text is removed from the snapshots.
  blobs  — git blob SHAs of SKILL.md texts that must not be redistributed here,
           whichever repository holds a copy. Removal is by content, so a copy
           of an excluded text in another repository goes too.

Removing text keeps the row and its pointer (repository, path, blob SHA) and
sets `skill_md_content` to null with `content_removed` saying why. The pipeline
never edits snapshots; this script does, and only when asked.

Usage:
  python crawlers/exclusions.py --check     # exit 1 if a snapshot still holds excluded text
  python crawlers/exclusions.py --apply     # remove excluded text from crawls/*/data.json
  python crawlers/exclusions.py --flag      # list texts whose frontmatter licence is
                                            #   proprietary or non-commercial (not on the list yet)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUSIONS = ROOT / "data" / "exclusions.json"
CRAWLS = ROOT / "crawls"


def git_blob_sha(text: str) -> str:
    """The git blob SHA-1 of a text, as GitHub reports it in `file_sha`."""
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _norm_repo(name: str) -> str:
    return name.strip().lower()


class Exclusions:
    def __init__(self, repos: set[str], blobs: set[str]):
        self.repos = {_norm_repo(r) for r in repos}
        self.blobs = {b.strip().lower() for b in blobs}

    def repo_excluded(self, repo: str | None) -> bool:
        return bool(repo) and _norm_repo(repo) in self.repos

    def blob_excluded(self, sha: str | None) -> bool:
        return bool(sha) and sha.strip().lower() in self.blobs

    def reason(self, repo: str | None, sha: str | None) -> str | None:
        if self.repo_excluded(repo):
            return "repo-excluded"
        if self.blob_excluded(sha):
            return "blob-excluded"
        return None


def load(path: Path = EXCLUSIONS) -> Exclusions:
    """Load the removal list. A missing file is an error, not an empty list,
    so a run can never silently skip the removals."""
    doc = json.loads(Path(path).read_text())
    repos = {e["repo"] for e in doc.get("repos", [])}
    blobs = {e["sha"] for e in doc.get("blobs", [])}
    for sha in blobs:
        if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha.lower()):
            raise ValueError(f"not a 40-character blob SHA: {sha!r}")
    return Exclusions(repos, blobs)


def _row_sha(row: dict) -> str | None:
    text = row.get("skill_md_content")
    if text:
        return git_blob_sha(text)
    return row.get("file_sha")


def scrub_rows(rows: list[dict], ex: Exclusions) -> int:
    """Remove excluded text from rows in place. Returns the number removed.

    Matches on the blob SHA of the stored text as well as the recorded
    `file_sha`, so a row whose metadata is stale is still caught."""
    removed = 0
    for row in rows:
        if not row.get("skill_md_content"):
            continue
        why = ex.reason(row.get("repo_full_name"), _row_sha(row)) or \
            ex.reason(None, row.get("file_sha"))
        if why:
            row["skill_md_content"] = None
            row["content_removed"] = why
            removed += 1
    return removed


def _snapshots() -> list[Path]:
    return sorted(CRAWLS.glob("*/data.json"))


def _write(path: Path, doc: dict, raw: str) -> None:
    # Keep the snapshot's own layout so the diff shows only the removals.
    ensure_ascii = raw.isascii()
    out = json.dumps(doc, indent=2, ensure_ascii=ensure_ascii)
    if raw.endswith("\n"):
        out += "\n"
    path.write_text(out)


def apply(ex: Exclusions, write: bool) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in _snapshots():
        raw = path.read_text()
        doc = json.loads(raw)
        n = scrub_rows(doc.get("results", []), ex)
        counts[path.parent.name] = n
        if n and write:
            _write(path, doc, raw)
    return counts


def flag_restrictive() -> dict[str, dict]:
    """Texts whose own frontmatter licence is proprietary or non-commercial."""
    try:
        from licensing import must_remove, skill_license
    except ImportError:  # imported as crawlers.exclusions
        from crawlers.licensing import must_remove, skill_license

    found: dict[str, dict] = {}
    for path in _snapshots():
        for row in json.loads(path.read_text()).get("results", []):
            text = row.get("skill_md_content")
            lic = skill_license(text)
            if lic and must_remove(lic):
                sha = git_blob_sha(text)
                entry = found.setdefault(sha, {"license": lic, "repos": set()})
                entry["repos"].add(row.get("repo_full_name"))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--flag", action="store_true")
    args = ap.parse_args()

    if args.flag:
        ex = load()
        for sha, e in sorted(flag_restrictive().items()):
            listed = "listed" if ex.blob_excluded(sha) else "NOT LISTED"
            print(f"{sha}  {listed}  {e['license']}  {', '.join(sorted(e['repos']))}")
        return 0

    counts = apply(load(), write=args.apply)
    total = sum(counts.values())
    for crawl, n in counts.items():
        print(f"{crawl}: {n} text(s) {'removed' if args.apply else 'still present'}")
    if args.check and total:
        print(f"{total} excluded text(s) remain in the snapshots", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
