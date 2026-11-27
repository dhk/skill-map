"""Delta crawl: find the SKILL.md files GitHub holds now and diff them against GitSkills.

GitSkills (Destefanis, Graziotin, Vaccargiu and Ortu, July 2026) found its files
with GitHub code search for `filename:SKILL.md`, partitioning the search by
file size because a query returns at most 1,000 results and its total_count is
unreliable (the dataset card reports about 349,000 for the filename query
against over 3.8M files retrieved). This module reruns that strategy, so the
two snapshots are comparable, and diffs the result against the GitSkills
occurrence table by blob SHA (docs/atlas/plan.md, ADR 0004):

- a blob SHA GitSkills never saw is a new text (added or changed since July,
  or indexed by GitHub since);
- a known blob SHA at a repository and path GitSkills didn't list is a new
  occurrence (a new copy of a known text);
- a GitSkills occurrence no longer found is listed as gone, and is only
  meaningful when the crawl finished with no capped or incomplete ranges.

How the search is split. A range `size:lo..hi` whose reported total_count is
near the cap is split into parts; a range is otherwise paged (100 per page, at
most 10 pages). If paging reaches 1,000 results the range is split anyway,
because total_count can undercount. A range one byte wide that still reaches
the cap (one text copied over 1,000 times has one size) can't be split by size;
it is re-queried with each PATH_SPLITS qualifier, results are merged by
repository and path, and the range is reported as capped in the manifest.

Code search allows 10 requests a minute per user (GitHub REST docs, "Search
code"), so the client waits between calls and backs off on 403, 429 and 5xx
responses. Progress is kept in SQLite under data/atlas/delta/.cache/, so an
interrupted run resumes where it stopped; a range is saved only when it is
complete. No file text is fetched: code search returns each file's repository,
path and blob SHA.

Outputs (data/atlas/delta/, Parquet kept out of git like the other Atlas tables;
manifest.json is committed):

- occurrence.parquet: one row per file found now: repository, path, blob SHA,
  platform folder, whether the basename is exactly SKILL.md, the size range
  it was found in, and new_text / new_occurrence / previous_blob_sha against
  GitSkills;
- gone.parquet: GitSkills occurrences not found now;
- manifest.json: method version, query, start and finish times, requests made,
  ranges by status, capped and incomplete ranges, counts, the GitSkills
  revision compared against, removal list hash and output hashes.

Repositories on the removal list (data/exclusions.json) are left out; files
whose text is on it are flagged removal_listed.

Usage:
    python -m crawlers.atlas.delta --max-requests 60      # a short trial run
    python -m crawlers.atlas.delta                         # run or resume the crawl
    python -m crawlers.atlas.delta --finish-only           # rebuild outputs from saved progress
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Callable

from crawlers import exclusions as removal

METHOD_VERSION = "delta-crawl/1.0.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "data" / "atlas" / "delta"
DEFAULT_GITSKILLS = REPO_ROOT / "data" / "atlas" / "gitskills"
DEFAULT_EXCLUSIONS = REPO_ROOT / "data" / "exclusions.json"

QUERY = "filename:SKILL.md"
MAX_SIZE = 393_215       # GitHub code search indexes files under 384 KB
CAP = 1000               # results one query can return
PER_PAGE = 100
SPLIT_AT = 900           # split before the cap: total_count is approximate
MAX_PARTS = 16
MIN_INTERVAL = 6.5       # seconds between search calls: under 10 a minute
PATH_SPLITS = (".claude", ".agents", ".codex", ".cursor", ".github", ".opencode",
               ".gemini", ".kiro", ".windsurf", "skills", "plugins")
PLATFORM_FOLDERS = {"claude", "codex", "agents", "github", "cursor", "gemini",
                    "windsurf", "opencode", "kiro"}

ATTRIBUTION = (
    "Delta crawl by the Skill Map project (https://github.com/dhk/skill-map), following "
    "the GitSkills collection method (Destefanis, Graziotin, Vaccargiu and Ortu, "
    "doi:10.5281/zenodo.21875637). Pointers only; no file text."
)

Search = Callable[[str, int], dict]


class SearchError(RuntimeError):
    """A query GitHub refused outright (for example a 422)."""


# ---------------------------------------------------------------- GitHub client

def github_token() -> str:
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        tok = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True,
                             timeout=20).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        tok = ""
    if not tok:
        raise SystemExit("delta: set GITHUB_TOKEN or sign in with `gh auth login`; "
                         "code search needs an authenticated user")
    return tok


class GitHubSearch:
    """Code search with the 10-a-minute limit, backoff and a request counter."""

    def __init__(self, token: str, min_interval: float = MIN_INTERVAL,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):
        self.token, self.min_interval, self.sleep, self.clock = token, min_interval, sleep, clock
        self.last = -1e9
        self.requests = 0

    def _wait_turn(self) -> None:
        gap = self.min_interval - (self.clock() - self.last)
        if gap > 0:
            self.sleep(gap)
        self.last = self.clock()

    def __call__(self, q: str, page: int) -> dict:
        url = "https://api.github.com/search/code?" + urllib.parse.urlencode(
            {"q": q, "per_page": PER_PAGE, "page": page})
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "skill-map-delta-crawl"})
        for attempt in range(8):
            self._wait_turn()
            self.requests += 1
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 422:
                    raise SearchError(f"GitHub refused the query {q!r} (422)") from e
                if e.code in (403, 429):
                    wait = _retry_wait(e.headers, attempt)
                    print(f"delta: rate limited, waiting {wait:.0f}s", file=sys.stderr)
                    self.sleep(wait)
                    continue
                if e.code >= 500:
                    self.sleep(min(300, 10 * 2 ** attempt))
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                self.sleep(min(300, 10 * 2 ** attempt))
        raise SearchError(f"gave up on {q!r} page {page} after repeated failures")


def _retry_wait(headers, attempt: int) -> float:
    if headers.get("Retry-After"):
        return float(headers["Retry-After"]) + 1
    if headers.get("X-RateLimit-Remaining") == "0" and headers.get("X-RateLimit-Reset"):
        return max(5.0, float(headers["X-RateLimit-Reset"]) - time.time() + 2)
    return min(600.0, 60.0 * 2 ** attempt)


# ---------------------------------------------------------------- state

SCHEMA = """
CREATE TABLE IF NOT EXISTS ranges (
  lo INTEGER, hi INTEGER, extra TEXT, status TEXT, reported INTEGER, retrieved INTEGER,
  incomplete INTEGER DEFAULT 0, PRIMARY KEY (lo, hi, extra));
CREATE TABLE IF NOT EXISTS hits (
  repo_key TEXT, path TEXT, repo TEXT, sha TEXT, lo INTEGER, hi INTEGER,
  PRIMARY KEY (repo_key, path));
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


def open_state(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    if not db.execute("SELECT 1 FROM ranges LIMIT 1").fetchone():
        db.execute("INSERT INTO ranges VALUES (0, ?, '', 'todo', NULL, NULL, 0)", (MAX_SIZE,))
        db.execute("INSERT OR REPLACE INTO meta VALUES ('started_at', ?)", (_now(),))
        db.execute("INSERT OR REPLACE INTO meta VALUES ('method_version', ?)", (METHOD_VERSION,))
        db.commit()
    return db


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def split_parts(lo: int, hi: int, reported: int) -> list[tuple[int, int]]:
    """Split [lo, hi] into equal byte ranges, more parts the more results are reported."""
    k = max(2, min(MAX_PARTS, math.ceil(reported / 600), hi - lo + 1))
    step = (hi - lo + 1) / k
    edges = sorted({lo + round(i * step) for i in range(k)} | {hi + 1})
    return [(a, b - 1) for a, b in zip(edges, edges[1:]) if b - 1 >= a]


def query_for(lo: int, hi: int, extra: str) -> str:
    size = f"size:{lo}" if lo == hi else f"size:{lo}..{hi}"
    return " ".join(p for p in (QUERY, size, extra) if p)


def fetch_range(search: Search, q: str, first: dict) -> tuple[list[dict], bool]:
    """Page through one query, starting from its first page; return items and whether any page was incomplete."""
    items, incomplete = list(first.get("items") or []), bool(first.get("incomplete_results"))
    page, last = 1, first
    while len(last.get("items") or []) == PER_PAGE and len(items) < CAP:
        page += 1
        last = search(q, page)
        incomplete |= bool(last.get("incomplete_results"))
        items.extend(last.get("items") or [])
    return items, incomplete


def crawl(db: sqlite3.Connection, search: Search, max_requests: int | None = None,
          counter: Callable[[], int] | None = None, log=print) -> bool:
    """Work through the range queue. Return True when no range is left to do."""
    counter = counter or (lambda: getattr(search, "requests", 0))
    while True:
        row = db.execute("SELECT lo, hi, extra FROM ranges WHERE status = 'todo' "
                         "ORDER BY lo, hi, extra LIMIT 1").fetchone()
        if row is None:
            return True
        if max_requests is not None and counter() >= max_requests:
            return False
        lo, hi, extra = row
        q = query_for(lo, hi, extra)
        try:
            first = search(q, 1)
        except SearchError as e:
            log(f"delta: {e}")
            db.execute("UPDATE ranges SET status = 'failed' WHERE lo = ? AND hi = ? AND extra = ?",
                       (lo, hi, extra))
            db.commit()
            continue
        reported = int(first.get("total_count") or 0)
        splittable = hi > lo and not extra
        if splittable and reported >= SPLIT_AT:
            _split(db, lo, hi, extra, reported)
            continue
        items, incomplete = fetch_range(search, q, first)
        if len(items) >= CAP and splittable:
            _split(db, lo, hi, extra, max(reported, CAP * 2))
            continue
        status = "done"
        if len(items) >= CAP:
            status = "capped"
            if not extra:  # one size, over the cap: try each path qualifier as well
                db.executemany("INSERT OR IGNORE INTO ranges VALUES (?, ?, ?, 'todo', NULL, NULL, 0)",
                               [(lo, hi, f"path:{p}") for p in PATH_SPLITS])
        _save(db, lo, hi, extra, status, reported, items, incomplete)
        log(f"delta: {q} -> {len(items)} files ({status}{', incomplete' if incomplete else ''}); "
            f"{counter()} requests so far")


def _split(db, lo, hi, extra, reported) -> None:
    db.execute("UPDATE ranges SET status = 'split', reported = ? WHERE lo = ? AND hi = ? AND extra = ?",
               (reported, lo, hi, extra))
    db.executemany("INSERT OR IGNORE INTO ranges VALUES (?, ?, ?, 'todo', NULL, NULL, 0)",
                   [(a, b, extra) for a, b in split_parts(lo, hi, reported)])
    db.commit()


def _save(db, lo, hi, extra, status, reported, items, incomplete) -> None:
    rows = []
    for it in items:
        repo = (it.get("repository") or {}).get("full_name")
        if not repo or not it.get("path") or not it.get("sha"):
            continue
        rows.append((repo.lower(), it["path"], repo, it["sha"], lo, hi))
    db.executemany("INSERT OR REPLACE INTO hits VALUES (?, ?, ?, ?, ?, ?)", rows)
    db.execute("UPDATE ranges SET status = ?, reported = ?, retrieved = ?, incomplete = ? "
               "WHERE lo = ? AND hi = ? AND extra = ?",
               (status, reported, len(items), int(incomplete), lo, hi, extra))
    db.commit()


# ---------------------------------------------------------------- diff and outputs

def platform_folder(path: str | None) -> str:
    """First dot-folder in the path, as in the GitSkills import."""
    for part in PurePosixPath(path or "").parts[:-1]:
        if part.startswith(".") and part[1:].lower() in PLATFORM_FOLDERS:
            return part[1:].lower()
    return "other"


def diff(hits: list[dict], gitskills: list[dict], ex: removal.Exclusions) -> tuple[list[dict], list[dict], dict]:
    """Compare current hits with GitSkills occurrences; return (occurrences, gone, counts)."""
    known_shas = {g["blob_sha"] for g in gitskills}
    before = {((g["repo_full_name"] or "").lower(), g["path"]): g["blob_sha"] for g in gitskills
              if not ex.repo_excluded(g["repo_full_name"])}
    rows, seen = [], set()
    for h in hits:
        if ex.repo_excluded(h["repo"]):
            continue
        key = (h["repo"].lower(), h["path"])
        seen.add(key)
        prev = before.get(key)
        rows.append({
            "repo_full_name": h["repo"], "path": h["path"], "blob_sha": h["sha"],
            "platform_folder": platform_folder(h["path"]),
            "basename_exact": PurePosixPath(h["path"]).name.lower() == "skill.md",
            "size_lo": h["lo"], "size_hi": h["hi"],
            "new_text": h["sha"] not in known_shas,
            "new_occurrence": prev is None,
            "previous_blob_sha": prev if prev is not None and prev != h["sha"] else None,
            "removal_listed": ex.blob_excluded(h["sha"]),
            "method_version": METHOD_VERSION,
        })
    gone = [{"repo_full_name": g["repo_full_name"], "path": g["path"], "blob_sha": g["blob_sha"],
             "method_version": METHOD_VERSION}
            for g in gitskills if not ex.repo_excluded(g["repo_full_name"])
            and ((g["repo_full_name"] or "").lower(), g["path"]) not in seen]
    counts = {
        "occurrences": len(rows),
        "repos": len({r["repo_full_name"].lower() for r in rows}),
        "distinct_texts": len({r["blob_sha"] for r in rows}),
        "new_texts": len({r["blob_sha"] for r in rows if r["new_text"]}),
        "occurrences_of_new_texts": sum(r["new_text"] for r in rows),
        "new_occurrences_of_known_texts": sum(r["new_occurrence"] and not r["new_text"] for r in rows),
        "changed_in_place": sum(r["previous_blob_sha"] is not None for r in rows),
        "gone": len(gone),
        "removal_listed": sum(r["removal_listed"] for r in rows),
        "basename_not_exact": sum(not r["basename_exact"] for r in rows),
    }
    return rows, gone, counts


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finish(db: sqlite3.Connection, out: Path, gitskills_dir: Path, exclusions_path: Path,
           requests: int, complete: bool) -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq

    hits = [dict(zip(("repo", "path", "sha", "lo", "hi"), r))
            for r in db.execute("SELECT repo, path, sha, lo, hi FROM hits ORDER BY repo_key, path")]
    occ = pq.read_table(gitskills_dir / "occurrence.parquet",
                        columns=["repo_full_name", "path", "blob_sha"]).to_pylist()
    ex = removal.load(exclusions_path)
    rows, gone, counts = diff(hits, occ, ex)
    out.mkdir(parents=True, exist_ok=True)
    outputs = []
    for name, data in (("occurrence.parquet", rows), ("gone.parquet", gone)):
        p = out / name
        pq.write_table(pa.Table.from_pylist(data), p)
        outputs.append({"path": name, "rows": len(data), "sha256": _sha256(p)})
    status = dict(db.execute("SELECT status, COUNT(*) FROM ranges GROUP BY status").fetchall())
    capped = [{"size": f"{lo}..{hi}", "extra": extra or None, "retrieved": n}
              for lo, hi, extra, n in db.execute(
                  "SELECT lo, hi, extra, retrieved FROM ranges WHERE status = 'capped' ORDER BY lo, extra")]
    incomplete = db.execute("SELECT COUNT(*) FROM ranges WHERE incomplete = 1").fetchone()[0]
    meta = dict(db.execute("SELECT key, value FROM meta").fetchall())
    gm_path = gitskills_dir / "manifest.json"
    gm = json.loads(gm_path.read_text(encoding="utf-8")) if gm_path.exists() else {}
    manifest = {
        "method_version": METHOD_VERSION,
        "attribution": ATTRIBUTION,
        "query": QUERY, "max_size": MAX_SIZE, "path_splits": list(PATH_SPLITS),
        "started_at": meta.get("started_at"), "finished_at": _now(),
        "complete": complete and not status.get("todo"),
        "requests_this_run": requests,
        "ranges": status,
        "capped_ranges": capped,
        "incomplete_ranges": incomplete,
        "failed_ranges": status.get("failed", 0),
        "gone_is_reliable": complete and not capped and not incomplete and not status.get("failed"),
        "compared_with": {"gitskills_revision": gm.get("revision") or gm.get("source", {}).get("revision"),
                          "occurrences": len(occ)},
        "removal_list": {"path": "data/exclusions.json", "sha256": _sha256(Path(exclusions_path))},
        "counts": counts,
        "outputs": outputs,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--gitskills", type=Path, default=DEFAULT_GITSKILLS,
                    help="GitSkills import output directory (occurrence.parquet)")
    ap.add_argument("--exclusions", type=Path, default=DEFAULT_EXCLUSIONS)
    ap.add_argument("--max-requests", type=int, default=None,
                    help="stop after this many search requests (resume later)")
    ap.add_argument("--finish-only", action="store_true",
                    help="write the outputs from saved progress without searching")
    args = ap.parse_args(argv)
    if not (args.gitskills / "occurrence.parquet").exists():
        print(f"delta: {args.gitskills / 'occurrence.parquet'} is missing: run the GitSkills "
              "import first (python -m crawlers.atlas.gitskills)", file=sys.stderr)
        return 2
    db = open_state(args.out / ".cache" / "state.sqlite")
    requests, complete = 0, False
    if not args.finish_only:
        client = GitHubSearch(github_token())
        try:
            complete = crawl(db, client, args.max_requests,
                             log=lambda m: print(m, file=sys.stderr))
        except KeyboardInterrupt:
            print("delta: stopped; run the same command to resume", file=sys.stderr)
        requests = client.requests
    else:
        complete = not db.execute("SELECT 1 FROM ranges WHERE status = 'todo' LIMIT 1").fetchone()
    left = db.execute("SELECT COUNT(*) FROM ranges WHERE status = 'todo'").fetchone()[0]
    m = finish(db, args.out, args.gitskills, args.exclusions, requests, complete)
    print(json.dumps({"complete": m["complete"], "ranges_left": left, **m["counts"]}, indent=2))
    if not m["complete"]:
        print("delta: not finished; run the same command to resume", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
