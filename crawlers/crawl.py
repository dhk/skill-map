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

QUERIES = [
    "filename:SKILL.md",
    "filename:SKILL.md claude",
    "filename:SKILL.md anthropic",
    "filename:skill.md",
    "filename:SKILLS.md",
]

RATE_LIMIT_BUFFER = 10  # pause when remaining <= this


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
        _raw_session = requests.Session()
        # raw.githubusercontent.com rejects Bearer/token auth via proxy — use no auth
    return _raw_session


def fetch_file_content(session: requests.Session, raw_url: str) -> tuple[str, str | None]:
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


def load_existing_results(crawl_dir: Path) -> tuple[list[dict], set[str]]:
    data_file = crawl_dir / "data.json"
    if not data_file.exists():
        return [], set()
    with open(data_file) as f:
        data = json.load(f)
    results = data.get("results", [])
    seen = {f"{r['repo_full_name']}::{r['file_path']}" for r in results}
    return results, seen


def write_data_json(crawl_dir: Path, crawl_id: str, crawl_date: str, results: list[dict]) -> None:
    unique_repos = len({r["repo_full_name"] for r in results})
    out = {
        "crawl_id": crawl_id,
        "crawl_date": crawl_date,
        "crawl_queries": QUERIES,
        "total_repos": unique_repos,
        "total_files": len(results),
        "results": results,
    }
    tmp = crawl_dir / "data.json.tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
    tmp.replace(crawl_dir / "data.json")


def write_meta_json(crawl_dir: Path, crawl_id: str, crawl_date: str, status: str,
                    results: list[dict], errors: int) -> None:
    unique_repos = len({r["repo_full_name"] for r in results})
    out = {
        "crawl_id": crawl_id,
        "status": status,
        "crawl_date": crawl_date,
        "queries_run": QUERIES,
        "total_repos": unique_repos,
        "total_files": len(results),
        "errors": errors,
    }
    tmp = crawl_dir / "crawl-meta.json.tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, indent=2)
    tmp.replace(crawl_dir / "crawl-meta.json")


def write_summary_md(crawl_dir: Path, crawl_id: str, crawl_date: str, results: list[dict], errors: int) -> None:
    unique_repos = len({r["repo_full_name"] for r in results})
    lines = [
        f"# SKILL.md Crawl: {crawl_id}",
        "",
        f"**Date:** {crawl_date}  ",
        f"**Total repos:** {unique_repos}  ",
        f"**Total files:** {len(results)}  ",
        f"**Errors:** {errors}  ",
        f"**Queries:** {', '.join(f'`{q}`' for q in QUERIES)}  ",
        "",
        "| Repo | Stars | Last Pushed | File Path | Description |",
        "|------|-------|-------------|-----------|-------------|",
    ]
    for r in results:
        repo = f"[{r['repo_full_name']}]({r['repo_url']})"
        stars = r.get("repo_stars", 0)
        pushed = (r.get("repo_last_pushed") or "")[:10]
        path = r.get("file_path", "")
        desc = (r.get("repo_description") or "").replace("|", "\\|")
        lines.append(f"| {repo} | {stars} | {pushed} | `{path}` | {desc} |")
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


def search_repo_files(session: requests.Session, repo: str) -> list[dict]:
    """Search a specific repo for all SKILL.md files via contents API tree walk."""
    results = []
    # Use git trees API to find all SKILL.md files efficiently
    resp = session.get(f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1")
    check_rate_limit(resp)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    tree = resp.json().get("tree", [])
    for item in tree:
        path = item.get("path", "")
        if item.get("type") == "blob" and Path(path).name.upper() == "SKILL.MD":
            raw_url = f"https://raw.githubusercontent.com/{repo}/HEAD/{path}"
            results.append({
                "repo_full_name": repo,
                "file_path": path,
                "file_raw_url": raw_url,
                "repo_url": f"https://github.com/{repo}",
            })
    return results


def load_crawl_list(path: Path) -> list[str]:
    with open(path) as f:
        data = json.load(f)
    return [r["repo"] for r in data.get("repos", []) if r.get("tier") != "list-only"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl GitHub for SKILL.md files.")
    parser.add_argument("--dry-run", action="store_true", help="Search only, no fetches or writes.")
    parser.add_argument("--crawl-list", type=Path, help="JSON crawl-list file to target specific repos instead of global search.")
    args = parser.parse_args()

    token = get_token()
    session = make_session(token)

    crawl_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Determine crawl directory
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

    # Search phase
    print("\nSearching GitHub...")
    seen_keys: set[str] = set()
    raw_items: list[tuple[str, str, str, str]] = []  # (repo_full_name, file_path, raw_url, repo_url)

    if args.crawl_list:
        # Repo-scoped mode: walk each repo's git tree
        target_repos = load_crawl_list(args.crawl_list)
        print(f"  Mode: repo-scoped ({len(target_repos)} repos from {args.crawl_list.name})")
        for repo_full_name in target_repos:
            print(f"  Scanning tree: {repo_full_name}")
            try:
                found = search_repo_files(session, repo_full_name)
            except requests.HTTPError as e:
                print(f"    [Error: {e}]")
                continue
            for f in found:
                key = f"{f['repo_full_name']}::{f['file_path']}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    raw_items.append((f["repo_full_name"], f["file_path"], f["file_raw_url"], f["repo_url"]))
            print(f"    → {len(found)} SKILL.md file(s) found")
            time.sleep(0.5)
    else:
        # Global search mode
        for query in QUERIES:
            print(f"  Query: {query}")
            try:
                items = search_code(session, query)
            except requests.HTTPError as e:
                print(f"  [Search error: {e}]")
                continue
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
                raw_items.append((repo_full_name, file_path, raw_url, repo_url))
                new_count += 1
            print(f"    → {new_count} new results ({len(raw_items)} total unique)")
            time.sleep(1)

    if args.dry_run:
        print(f"\n[Dry run] Would fetch {len(raw_items)} file(s) across repos:")
        for repo_full_name, file_path, raw_url, repo_url in raw_items:
            print(f"  {repo_full_name} / {file_path}")
        return

    # Load existing results for resumability
    results, already_done = load_existing_results(crawl_dir)
    errors = sum(1 for r in results if r.get("fetch_error"))

    # Set up interrupt handler
    interrupted = False

    def handle_interrupt(sig, frame):
        nonlocal interrupted
        interrupted = True
        print("\n\n[Interrupted — saving state...]")
        write_data_json(crawl_dir, crawl_id, crawl_date, results)
        write_meta_json(crawl_dir, crawl_id, crawl_date, "interrupted", results, errors)
        sys.exit(1)

    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    write_meta_json(crawl_dir, crawl_id, crawl_date, "running", results, errors)

    # Fetch phase
    print(f"\nFetching file contents for {len(raw_items)} unique result(s)...")
    processed = 0

    for repo_full_name, file_path, raw_url, repo_url in raw_items:
        key = f"{repo_full_name}::{file_path}"
        if key in already_done:
            continue

        print(f"Crawling {repo_full_name} ({repo_url})...")

        result: dict = {
            "repo_full_name": repo_full_name,
            "repo_url": repo_url,
            "repo_description": "",
            "repo_stars": 0,
            "repo_forks": 0,
            "repo_topics": [],
            "repo_last_pushed": "",
            "repo_owner_type": "",
            "file_path": file_path,
            "file_raw_url": raw_url,
            "skill_md_content": "",
            "fetch_error": None,
        }

        # Fetch repo metadata
        try:
            meta = fetch_repo_meta(session, repo_full_name)
            result.update(meta)
        except Exception as e:
            result["fetch_error"] = f"repo_meta: {e}"
            errors += 1
            print(f"  ↳ fetch error (repo meta: {e})")
            results.append(result)
            already_done.add(key)
            processed += 1
            write_data_json(crawl_dir, crawl_id, crawl_date, results)
            write_meta_json(crawl_dir, crawl_id, crawl_date, "running", results, errors)
            if processed % 10 == 0:
                unique_repos = len({r["repo_full_name"] for r in results})
                print(f"[{unique_repos} repos processed | {len(results)} skills found | {errors} errors]")
            continue

        # Fetch file content
        time.sleep(1)
        try:
            content, error = fetch_file_content(session, raw_url)
            if error:
                result["fetch_error"] = f"file_content: {error}"
                errors += 1
                print(f"  ↳ fetch error ({error})")
            else:
                result["skill_md_content"] = content
                print(f"  ↳ found 1 skill(s)")
        except Exception as e:
            result["fetch_error"] = f"file_content: {e}"
            errors += 1
            print(f"  ↳ fetch error ({e})")

        results.append(result)
        already_done.add(key)
        processed += 1

        write_data_json(crawl_dir, crawl_id, crawl_date, results)
        write_meta_json(crawl_dir, crawl_id, crawl_date, "running", results, errors)

        if processed % 10 == 0:
            unique_repos = len({r["repo_full_name"] for r in results})
            print(f"[{unique_repos} repos processed | {len(results)} skills found | {errors} errors]")

    # Write final outputs
    write_data_json(crawl_dir, crawl_id, crawl_date, results)
    write_meta_json(crawl_dir, crawl_id, crawl_date, "complete", results, errors)
    write_summary_md(crawl_dir, crawl_id, crawl_date, results, errors)

    unique_repos = len({r["repo_full_name"] for r in results})
    skills_found = sum(1 for r in results if not r.get("fetch_error"))

    print(f"""
✓ Crawl complete: {crawl_id}
  Repos processed: {unique_repos}
  Skills found:    {skills_found}
  Errors:          {errors}
  Output:          {crawl_dir}/
""")

    # Git commit and push
    git_commit_and_push(crawl_id)


if __name__ == "__main__":
    main()
