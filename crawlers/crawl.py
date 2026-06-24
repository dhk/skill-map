#!/usr/bin/env python3
"""GitHub SKILL.md crawler."""

import argparse
import json
import os
import re
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
CRAWLS_DIR = BASE_DIR / "crawls"
DISCOVERY_DIR = BASE_DIR / "crawlers" / "discovery-queue"

QUERIES = [
    "filename:SKILL.md",
    "filename:SKILL.md claude",
    "filename:SKILL.md anthropic",
    "filename:skill.md",
    "filename:SKILLS.md",
]

RATE_LIMIT_BUFFER = 10


def get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return token


def make_session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    return s


def check_rate_limit(resp: requests.Response) -> None:
    remaining = int(resp.headers.get("X-RateLimit-Remaining", 999))
    reset_ts = int(resp.headers.get("X-RateLimit-Reset", 0))
    if remaining <= RATE_LIMIT_BUFFER and reset_ts:
        wait = max(0, reset_ts - int(time.time())) + 2
        print(f"\n  [Rate limit low ({remaining} remaining). Sleeping {wait}s until reset...]")
        time.sleep(wait)


def search_code(session: requests.Session, query: str) -> list[dict]:
    results = []
    page = 1
    per_page = 100
    while True:
        resp = session.get(
            "https://api.github.com/search/code",
            params={"q": query, "per_page": per_page, "page": page},
        )
        check_rate_limit(resp)
        if resp.status_code == 422:
            print(f"  [Query '{query}' returned 422 — skipping]")
            break
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        results.extend(items)
        if len(items) < per_page or len(results) >= data.get("total_count", 0):
            break
        page += 1
        time.sleep(1)
    return results


def fetch_repo_meta(session: requests.Session, repo_full_name: str) -> dict:
    resp = session.get(f"https://api.github.com/repos/{repo_full_name}")
    check_rate_limit(resp)
    resp.raise_for_status()
    d = resp.json()
    return {
        "repo_description": d.get("description") or "",
        "repo_stars": d.get("stargazers_count", 0),
        "repo_forks": d.get("forks_count", 0),
        "repo_topics": d.get("topics", []),
        "repo_last_pushed": d.get("pushed_at") or "",
        "repo_owner_type": d.get("owner", {}).get("type") or "",
    }


_raw_session: requests.Session | None = None

def get_raw_session() -> requests.Session:
    global _raw_session
    if _raw_session is None:
        # raw.githubusercontent.com rejects Bearer/token auth via proxy — use no auth
        _raw_session = requests.Session()
    return _raw_session


def fetch_file_content(raw_url: str) -> tuple[str, str | None]:
    resp = get_raw_session().get(raw_url)
    if resp.status_code != 200:
        return "", f"HTTP {resp.status_code}"
    return resp.text, None


def next_crawl_n() -> int:
    CRAWLS_DIR.mkdir(parents=True, exist_ok=True)
    existing = [d.name for d in CRAWLS_DIR.iterdir() if d.is_dir() and re.match(r"crawl-\d+-", d.name)]
    if not existing:
        return 1
    nums = [int(re.match(r"crawl-(\d+)-", n).group(1)) for n in existing]
    return max(nums) + 1


def find_today_crawl_dir(crawl_date: str) -> Path | None:
    if not CRAWLS_DIR.exists():
        return None
    for d in CRAWLS_DIR.iterdir():
        if d.is_dir() and re.match(rf"crawl-\d+-{re.escape(crawl_date)}", d.name):
            return d
    return None


def load_existing_results(crawl_dir: Path) -> tuple[list[dict], dict[str, str]]:
    """Returns (results, sha_map) where sha_map is key -> file_sha."""
    data_file = crawl_dir / "data.json"
    if not data_file.exists():
        return [], {}
    with open(data_file) as f:
        data = json.load(f)
    results = data.get("results", [])
    sha_map = {
        f"{r['repo_full_name']}::{r['file_path']}": r.get("file_sha", "")
        for r in results
        if not r.get("fetch_error")
    }
    return results, sha_map


def write_data_json(crawl_dir: Path, crawl_id: str, crawl_date: str,
                    results: list[dict], queries: list[str]) -> None:
    unique_repos = len({r["repo_full_name"] for r in results})
    repo_breakdown = {}
    for r in results:
        repo_breakdown.setdefault(r["repo_full_name"], {"skills": 0, "errors": 0})
        if r.get("fetch_error"):
            repo_breakdown[r["repo_full_name"]]["errors"] += 1
        else:
            repo_breakdown[r["repo_full_name"]]["skills"] += 1
    out = {
        "crawl_id": crawl_id,
        "crawl_date": crawl_date,
        "crawl_queries": queries,
        "total_repos": unique_repos,
        "total_files": len(results),
        "repo_breakdown": repo_breakdown,
        "results": results,
    }
    tmp = crawl_dir / "data.json.tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
    tmp.replace(crawl_dir / "data.json")


def write_meta_json(crawl_dir: Path, crawl_id: str, crawl_date: str, status: str,
                    results: list[dict], errors: int, queries: list[str]) -> None:
    unique_repos = len({r["repo_full_name"] for r in results})
    repo_breakdown = {}
    for r in results:
        repo_breakdown.setdefault(r["repo_full_name"], {"skills": 0, "errors": 0})
        if r.get("fetch_error"):
            repo_breakdown[r["repo_full_name"]]["errors"] += 1
        else:
            repo_breakdown[r["repo_full_name"]]["skills"] += 1
    out = {
        "crawl_id": crawl_id,
        "status": status,
        "crawl_date": crawl_date,
        "queries_run": queries,
        "total_repos": unique_repos,
        "total_files": len(results),
        "errors": errors,
        "repo_breakdown": repo_breakdown,
    }
    tmp = crawl_dir / "crawl-meta.json.tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
    tmp.replace(crawl_dir / "crawl-meta.json")


def write_summary_md(crawl_dir: Path, crawl_id: str, crawl_date: str,
                     results: list[dict], errors: int, queries: list[str]) -> None:
    unique_repos = len({r["repo_full_name"] for r in results})
    lines = [
        f"# SKILL.md Crawl: {crawl_id}",
        "",
        f"**Date:** {crawl_date}  ",
        f"**Total repos:** {unique_repos}  ",
        f"**Total files:** {len(results)}  ",
        f"**Errors:** {errors}  ",
        f"**Queries:** {', '.join(f'`{q}`' for q in queries)}  ",
        "",
        "| Repo | Source | Stars | Last Pushed | File Path | Description |",
        "|------|--------|-------|-------------|-----------|-------------|",
    ]
    for r in results:
        if r.get("fetch_error"):
            continue
        repo = f"[{r['repo_full_name']}]({r['repo_url']})"
        source = r.get("repo_source", "")
        stars = r.get("repo_stars", 0)
        pushed = (r.get("repo_last_pushed") or "")[:10]
        path = r.get("file_path", "")
        desc = (r.get("repo_description") or "").replace("|", "\\|")
        lines.append(f"| {repo} | {source} | {stars} | {pushed} | `{path}` | {desc} |")
    with open(crawl_dir / "summary.md", "w") as f:
        f.write("\n".join(lines) + "\n")


def git_commit_and_push(crawl_id: str) -> None:
    import subprocess
    rel = f"crawls/{crawl_id}/"
    cmds = [
        ["git", "-C", str(BASE_DIR), "add", rel],
        ["git", "-C", str(BASE_DIR), "commit", "-m", f"feat: {crawl_id} — SKILL.md sweep"],
        ["git", "-C", str(BASE_DIR), "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  git error: {result.stderr.strip()}", file=sys.stderr)
            return
    print("  [Committed and pushed]")


# ---------------------------------------------------------------------------
# Repo-type handlers
# ---------------------------------------------------------------------------

def walk_repo_tree(session: requests.Session, repo: str) -> list[dict]:
    """Return list of {file_path, file_sha, file_raw_url, repo_url} for all SKILL.md blobs."""
    resp = session.get(f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1")
    check_rate_limit(resp)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    results = []
    for item in resp.json().get("tree", []):
        path = item.get("path", "")
        if item.get("type") == "blob" and Path(path).name.upper() == "SKILL.MD":
            results.append({
                "repo_full_name": repo,
                "file_path": path,
                "file_sha": item.get("sha", ""),
                "file_raw_url": f"https://raw.githubusercontent.com/{repo}/HEAD/{path}",
                "repo_url": f"https://github.com/{repo}",
            })
    return results


def process_index_only(session: requests.Session, repo: str, crawl_id: str,
                       existing_repos: set[str], dry_run: bool) -> list[dict]:
    """Fetch README, extract GitHub repo links, write discovery queue."""
    print(f"  [index-only] Parsing {repo} for outbound repo links...")
    candidates = []
    for readme_path in ("README.md", "readme.md", "README"):
        resp = get_raw_session().get(
            f"https://raw.githubusercontent.com/{repo}/HEAD/{readme_path}"
        )
        if resp.status_code == 200:
            links = re.findall(
                r"https://github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)",
                resp.text,
            )
            for link in links:
                # Strip trailing punctuation / fragments
                link = re.sub(r"[/#\)\]\'\">].*$", "", link)
                parts = link.split("/")
                if len(parts) == 2 and link not in existing_repos and link != repo:
                    candidates.append(link)
            break

    # Deduplicate
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    print(f"    → {len(unique)} new candidate repo(s) discovered")

    if not dry_run and unique:
        DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
        out_path = DISCOVERY_DIR / f"{crawl_id}-from-{repo.replace('/', '_')}.json"
        with open(out_path, "w") as f:
            json.dump({
                "crawl_id": crawl_id,
                "source_repo": repo,
                "source_type": "index-only",
                "discovered": [{"repo": r, "status": "pending"} for r in unique],
            }, f, indent=2)
        print(f"    → Written to {out_path.relative_to(BASE_DIR)}")

    return unique


# ---------------------------------------------------------------------------
# Crawl list loading
# ---------------------------------------------------------------------------

def load_crawl_list(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data.get("repos", [])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl GitHub for SKILL.md files.")
    parser.add_argument("--dry-run", action="store_true", help="Search only; no fetches, no writes, no commits.")
    parser.add_argument("--crawl-list", type=Path, help="JSON crawl-list file for repo-scoped mode.")
    args = parser.parse_args()

    token = get_token()
    session = make_session(token)

    crawl_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    existing_dir = find_today_crawl_dir(crawl_date)
    if existing_dir:
        crawl_id = existing_dir.name
        crawl_dir = existing_dir
        print(f"Resuming existing crawl: {crawl_id}")
    else:
        n = next_crawl_n()
        crawl_id = f"crawl-{n}-{crawl_date}"
        crawl_dir = CRAWLS_DIR / crawl_id
        crawl_dir.mkdir(parents=True, exist_ok=True)
        print(f"Starting new crawl: {crawl_id}")

    if args.dry_run:
        print("\n-- DRY RUN MODE --")

    # -----------------------------------------------------------------------
    # Discovery / search phase
    # -----------------------------------------------------------------------
    print("\nSearching GitHub...")

    # raw_items: list of (repo_full_name, file_path, file_sha, raw_url, repo_url, repo_source)
    raw_items: list[tuple] = []
    seen_keys: set[str] = set()
    queries_run: list[str] = []

    if args.crawl_list:
        repo_entries = load_crawl_list(args.crawl_list)
        all_repos = {e["repo"] for e in repo_entries}
        print(f"  Mode: repo-scoped ({len(repo_entries)} entries from {args.crawl_list.name})")

        for entry in repo_entries:
            repo = entry["repo"]
            repo_type = entry.get("type", "domain-collection")
            tier = entry.get("tier", "medium")

            # index-only: mine for discovery, don't crawl for skills
            if repo_type == "index-only":
                process_index_only(session, repo, crawl_id, all_repos, args.dry_run)
                time.sleep(0.5)
                continue

            print(f"  Scanning tree: {repo} [{repo_type}]")
            try:
                found = walk_repo_tree(session, repo)
            except requests.HTTPError as e:
                print(f"    [Error: {e}]")
                continue

            for f in found:
                key = f"{f['repo_full_name']}::{f['file_path']}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    raw_items.append((
                        f["repo_full_name"], f["file_path"], f["file_sha"],
                        f["file_raw_url"], f["repo_url"], repo_type,
                    ))
            print(f"    → {len(found)} SKILL.md file(s)")
            time.sleep(0.5)

        queries_run = [f"crawl-list:{args.crawl_list.name}"]

    else:
        # Global search mode
        for query in QUERIES:
            print(f"  Query: {query}")
            try:
                items = search_code(session, query)
            except requests.HTTPError as e:
                print(f"  [Search error: {e}]")
                continue
            queries_run.append(query)
            new_count = 0
            for item in items:
                repo = item.get("repository", {})
                repo_full_name = repo.get("full_name", "")
                file_path = item.get("path", "")
                key = f"{repo_full_name}::{file_path}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                raw_url = item.get("html_url", "").replace(
                    "https://github.com/", "https://raw.githubusercontent.com/"
                ).replace("/blob/", "/")
                repo_url = repo.get("html_url", f"https://github.com/{repo_full_name}")
                raw_items.append((repo_full_name, file_path, "", raw_url, repo_url, "search"))
                new_count += 1
            print(f"    → {new_count} new results ({len(raw_items)} total unique)")
            time.sleep(1)

    if args.dry_run:
        print(f"\n[Dry run] Would fetch {len(raw_items)} file(s):")
        for repo_full_name, file_path, sha, raw_url, repo_url, source in raw_items:
            sha_label = f" sha:{sha[:7]}" if sha else ""
            print(f"  [{source}] {repo_full_name} / {file_path}{sha_label}")
        return

    # -----------------------------------------------------------------------
    # Fetch phase — with SHA-diff incrementality
    # -----------------------------------------------------------------------
    results, sha_map = load_existing_results(crawl_dir)
    errors = sum(1 for r in results if r.get("fetch_error"))

    # Index existing results for fast lookup and in-place update
    result_index: dict[str, int] = {
        f"{r['repo_full_name']}::{r['file_path']}": i
        for i, r in enumerate(results)
    }

    def handle_interrupt(sig, frame):
        print("\n\n[Interrupted — saving state...]")
        write_data_json(crawl_dir, crawl_id, crawl_date, results, queries_run)
        write_meta_json(crawl_dir, crawl_id, crawl_date, "interrupted", results, errors, queries_run)
        sys.exit(1)

    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    write_meta_json(crawl_dir, crawl_id, crawl_date, "running", results, errors, queries_run)

    skipped = 0
    fetched = 0
    processed = 0

    print(f"\nFetching file contents for {len(raw_items)} unique result(s)...")

    for repo_full_name, file_path, file_sha, raw_url, repo_url, repo_source in raw_items:
        key = f"{repo_full_name}::{file_path}"
        is_canonical = repo_source == "canonical"

        # SHA-diff skip: if we have a clean result with the same SHA, skip unless canonical
        if not is_canonical and key in sha_map and sha_map[key] == file_sha and file_sha:
            skipped += 1
            continue

        print(f"Crawling {repo_full_name} ({repo_url})...")

        result: dict = {
            "repo_full_name": repo_full_name,
            "repo_url": repo_url,
            "repo_source": repo_source,
            "repo_description": "",
            "repo_stars": 0,
            "repo_forks": 0,
            "repo_topics": [],
            "repo_last_pushed": "",
            "repo_owner_type": "",
            "file_path": file_path,
            "file_sha": file_sha,
            "file_raw_url": raw_url,
            "skill_md_content": "",
            "fetch_error": None,
        }

        # Fetch repo metadata (reuse from existing result if SHA unchanged and not canonical)
        existing_idx = result_index.get(key)
        if existing_idx is not None and not is_canonical:
            existing = results[existing_idx]
            result.update({k: existing[k] for k in (
                "repo_description", "repo_stars", "repo_forks",
                "repo_topics", "repo_last_pushed", "repo_owner_type",
            ) if k in existing})
        else:
            try:
                meta = fetch_repo_meta(session, repo_full_name)
                result.update(meta)
            except Exception as e:
                result["fetch_error"] = f"repo_meta: {e}"
                errors += 1
                print(f"  ↳ fetch error (repo meta: {e})")
                _upsert_result(results, result_index, result)
                processed += 1
                write_data_json(crawl_dir, crawl_id, crawl_date, results, queries_run)
                write_meta_json(crawl_dir, crawl_id, crawl_date, "running", results, errors, queries_run)
                if processed % 10 == 0:
                    _print_tally(results, errors, skipped)
                continue

        # Fetch file content
        time.sleep(1)
        try:
            content, error = fetch_file_content(raw_url)
            if error:
                result["fetch_error"] = f"file_content: {error}"
                errors += 1
                print(f"  ↳ fetch error ({error})")
            else:
                result["skill_md_content"] = content
                fetched += 1
                sha_label = f" (sha changed)" if key in sha_map and sha_map[key] != file_sha else ""
                print(f"  ↳ fetched{sha_label}")
        except Exception as e:
            result["fetch_error"] = f"file_content: {e}"
            errors += 1
            print(f"  ↳ fetch error ({e})")

        _upsert_result(results, result_index, result)
        processed += 1

        write_data_json(crawl_dir, crawl_id, crawl_date, results, queries_run)
        write_meta_json(crawl_dir, crawl_id, crawl_date, "running", results, errors, queries_run)

        if processed % 10 == 0:
            _print_tally(results, errors, skipped)

    # -----------------------------------------------------------------------
    # Finalise
    # -----------------------------------------------------------------------
    write_data_json(crawl_dir, crawl_id, crawl_date, results, queries_run)
    write_meta_json(crawl_dir, crawl_id, crawl_date, "complete", results, errors, queries_run)
    write_summary_md(crawl_dir, crawl_id, crawl_date, results, errors, queries_run)

    unique_repos = len({r["repo_full_name"] for r in results})
    skills_found = sum(1 for r in results if not r.get("fetch_error"))

    print(f"""
✓ Crawl complete: {crawl_id}
  Repos processed: {unique_repos}
  Skills found:    {skills_found}
  Fetched (new/changed): {fetched}
  Skipped (unchanged):   {skipped}
  Errors:          {errors}
  Output:          {crawl_dir}/
""")

    git_commit_and_push(crawl_id)


def _upsert_result(results: list[dict], index: dict[str, int], result: dict) -> None:
    key = f"{result['repo_full_name']}::{result['file_path']}"
    if key in index:
        results[index[key]] = result
    else:
        index[key] = len(results)
        results.append(result)


def _print_tally(results: list[dict], errors: int, skipped: int) -> None:
    unique_repos = len({r["repo_full_name"] for r in results})
    skills = sum(1 for r in results if not r.get("fetch_error"))
    print(f"[{unique_repos} repos | {skills} skills | {errors} errors | {skipped} skipped]")


if __name__ == "__main__":
    main()
