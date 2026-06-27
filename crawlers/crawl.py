#!/usr/bin/env python3
"""GitHub SKILL.md crawler — uses PyGithub, httpx, rich, typer, tenacity."""

from __future__ import annotations

import json
import os
import re
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import typer
from github import Auth, Github, GithubException, RateLimitExceededException
from github.ContentFile import ContentFile
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.table import Table
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CRAWLS_DIR = BASE_DIR / "crawls"
DISCOVERY_DIR = BASE_DIR / "crawlers" / "discovery-queue"

console = Console()
app = typer.Typer(help="Crawl GitHub for SKILL.md files.", add_completion=False)

GLOBAL_QUERIES = [
    "filename:SKILL.md",
    "filename:SKILL.md claude",
    "filename:SKILL.md anthropic",
    "filename:skill.md",
    "filename:SKILLS.md",
]


# ---------------------------------------------------------------------------
# GitHub helpers — PyGithub handles auth, rate-limit headers, pagination
# ---------------------------------------------------------------------------

def make_gh(token: str) -> Github:
    return Github(auth=Auth.Token(token), per_page=100)


def wait_for_rate_limit(gh: Github, resource: str = "search") -> None:
    rl = gh.get_rate_limit()
    core = getattr(rl, resource)
    if core.remaining <= 5:
        reset = core.reset.replace(tzinfo=timezone.utc)
        wait = max(0, (reset - datetime.now(timezone.utc)).total_seconds()) + 2
        console.print(f"  [yellow]Rate limit low ({core.remaining} remaining). Sleeping {wait:.0f}s…[/yellow]")
        time.sleep(wait)


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(RateLimitExceededException),
    reraise=True,
)
def search_code_page(gh: Github, query: str, page: int):
    wait_for_rate_limit(gh, "search")
    return gh.search_code(query).get_page(page)


def walk_repo_tree(gh: Github, repo_full_name: str) -> list[dict]:
    """Return all SKILL.md blobs with their git SHA via the trees API."""
    try:
        repo = gh.get_repo(repo_full_name)
        tree = repo.get_git_tree(sha="HEAD", recursive=True)
    except GithubException as e:
        if e.status == 404:
            return []
        raise
    results = []
    for item in tree.tree:
        if item.type == "blob" and Path(item.path).name.upper() == "SKILL.MD":
            is_gemini = item.path.startswith(".gemini/")
            results.append({
                "repo_full_name": repo_full_name,
                "file_path": item.path,
                "file_sha": item.sha,
                "file_raw_url": f"https://raw.githubusercontent.com/{repo_full_name}/HEAD/{item.path}",
                "repo_url": f"https://github.com/{repo_full_name}",
                "file_format": "gemini" if is_gemini else "claude",
            })
    return results


def get_repo_meta(gh: Github, repo_full_name: str) -> dict:
    repo = gh.get_repo(repo_full_name)
    return {
        "repo_description": repo.description or "",
        "repo_stars": repo.stargazers_count,
        "repo_forks": repo.forks_count,
        "repo_topics": repo.get_topics(),
        "repo_last_pushed": repo.pushed_at.isoformat() if repo.pushed_at else "",
        "repo_owner_type": repo.owner.type,
    }


# ---------------------------------------------------------------------------
# Raw file fetch — unauthenticated (auth causes 404 via proxy on raw.gh.com)
# ---------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(httpx.TransportError),
    reraise=True,
)
def fetch_raw(url: str) -> tuple[str, str | None]:
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    if resp.status_code != 200:
        return "", f"HTTP {resp.status_code}"
    return resp.text, None


# ---------------------------------------------------------------------------
# Crawl directory helpers
# ---------------------------------------------------------------------------

def next_crawl_n() -> int:
    CRAWLS_DIR.mkdir(parents=True, exist_ok=True)
    existing = [d.name for d in CRAWLS_DIR.iterdir()
                if d.is_dir() and re.match(r"crawl-\d+-", d.name)]
    if not existing:
        return 1
    return max(int(re.match(r"crawl-(\d+)-", n).group(1)) for n in existing) + 1


def find_today_dir(crawl_date: str) -> Path | None:
    if not CRAWLS_DIR.exists():
        return None
    for d in CRAWLS_DIR.iterdir():
        if d.is_dir() and re.match(rf"crawl-\d+-{re.escape(crawl_date)}", d.name):
            return d
    return None


def load_existing(crawl_dir: Path) -> tuple[list[dict], dict[str, str]]:
    """(results, sha_map{key->sha}) — sha_map only for clean (no-error) entries."""
    path = crawl_dir / "data.json"
    if not path.exists():
        return [], {}
    data = json.loads(path.read_text())
    results = data.get("results", [])
    sha_map = {
        f"{r['repo_full_name']}::{r['file_path']}": r.get("file_sha", "")
        for r in results if not r.get("fetch_error")
    }
    return results, sha_map


def _repo_breakdown(results: list[dict]) -> dict:
    bd: dict[str, dict] = {}
    for r in results:
        bd.setdefault(r["repo_full_name"], {"skills": 0, "errors": 0})
        if r.get("fetch_error"):
            bd[r["repo_full_name"]]["errors"] += 1
        else:
            bd[r["repo_full_name"]]["skills"] += 1
    return bd


def write_data(crawl_dir: Path, crawl_id: str, crawl_date: str,
               results: list[dict], queries: list[str]) -> None:
    out = {
        "crawl_id": crawl_id,
        "crawl_date": crawl_date,
        "crawl_queries": queries,
        "total_repos": len({r["repo_full_name"] for r in results}),
        "total_files": len(results),
        "repo_breakdown": _repo_breakdown(results),
        "results": results,
    }
    tmp = crawl_dir / "data.json.tmp"
    tmp.write_text(json.dumps(out, indent=2))
    tmp.replace(crawl_dir / "data.json")


def write_meta(crawl_dir: Path, crawl_id: str, crawl_date: str, status: str,
               results: list[dict], errors: int, queries: list[str],
               quality: dict | None = None) -> None:
    out = {
        "crawl_id": crawl_id,
        "status": status,
        "crawl_date": crawl_date,
        "queries_run": queries,
        "total_repos": len({r["repo_full_name"] for r in results}),
        "total_files": len(results),
        "errors": errors,
        "repo_breakdown": _repo_breakdown(results),
    }
    if quality:
        out["input_quality"] = quality
    tmp = crawl_dir / "crawl-meta.json.tmp"
    tmp.write_text(json.dumps(out, indent=2))
    tmp.replace(crawl_dir / "crawl-meta.json")


def write_summary(crawl_dir: Path, crawl_id: str, crawl_date: str,
                  results: list[dict], errors: int, queries: list[str]) -> None:
    ok = [r for r in results if not r.get("fetch_error")]
    unique_repos = len({r["repo_full_name"] for r in results})
    lines = [
        f"# SKILL.md Crawl: {crawl_id}",
        "",
        f"**Date:** {crawl_date}  ",
        f"**Total repos:** {unique_repos}  ",
        f"**Total files:** {len(ok)}  ",
        f"**Errors:** {errors}  ",
        f"**Queries:** {', '.join(f'`{q}`' for q in queries)}  ",
        "",
        "| Repo | Type | Stars | Last Pushed | File Path | Description |",
        "|------|------|-------|-------------|-----------|-------------|",
    ]
    for r in ok:
        repo = f"[{r['repo_full_name']}]({r['repo_url']})"
        rtype = r.get("repo_source", "")
        stars = r.get("repo_stars", 0)
        pushed = (r.get("repo_last_pushed") or "")[:10]
        path = r.get("file_path", "")
        desc = (r.get("repo_description") or "").replace("|", "\\|")[:80]
        lines.append(f"| {repo} | {rtype} | {stars} | {pushed} | `{path}` | {desc} |")
    (crawl_dir / "summary.md").write_text("\n".join(lines) + "\n")


def upsert(results: list[dict], index: dict[str, int], result: dict) -> None:
    key = f"{result['repo_full_name']}::{result['file_path']}"
    if key in index:
        results[index[key]] = result
    else:
        index[key] = len(results)
        results.append(result)


def git_commit_push(crawl_id: str) -> None:
    import subprocess
    rel = f"crawls/{crawl_id}/"
    for cmd in [
        ["git", "-C", str(BASE_DIR), "add", rel],
        ["git", "-C", str(BASE_DIR), "commit", "-m", f"feat: {crawl_id} — SKILL.md sweep"],
        ["git", "-C", str(BASE_DIR), "push"],
    ]:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            console.print(f"  [red]git: {r.stderr.strip()}[/red]")
            return
    console.print("  [green]Committed and pushed[/green]")


# ---------------------------------------------------------------------------
# Crawl-list helpers
# ---------------------------------------------------------------------------

def load_crawl_list(path: Path) -> tuple[list[dict], dict]:
    """Load a crawl list from JSON or Markdown.

    Markdown format: optional YAML frontmatter (--- ... ---) for list metadata,
    plus a Markdown table whose header includes a `repo` column. Extra columns
    (type/tier/notes) become per-repo fields.
    """
    if path.suffix.lower() in (".md", ".markdown"):
        return _load_crawl_list_md(path.read_text())
    raw = json.loads(path.read_text())
    meta = {k: v for k, v in raw.items() if k != "repos"}
    return raw.get("repos", []), meta


def _load_crawl_list_md(text: str) -> tuple[list[dict], dict]:
    meta: dict = {}
    body = text
    m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if m:
        body = m.group(2)
        for line in m.group(1).splitlines():
            mm = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
            if mm:
                meta[mm.group(1).strip()] = mm.group(2).strip()
    repos: list[dict] = []
    header: list[str] | None = None
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):   # separator row
            continue
        if header is None:
            header = [c.lower() for c in cells]
            continue
        row = dict(zip(header, cells))
        if row.get("repo"):
            repos.append(row)
    return repos, meta


def input_quality_metrics(
    list_meta: dict,
    repo_outcomes: dict[str, str],  # repo -> "found" | "empty" | "error" | "not_found"
    results: list[dict],
) -> dict:
    """Summarise how useful a crawl input list was."""
    repos = list(repo_outcomes.keys())
    n_total = len(repos)
    n_found = sum(1 for v in repo_outcomes.values() if v == "found")
    n_empty = sum(1 for v in repo_outcomes.values() if v == "empty")
    n_not_found = sum(1 for v in repo_outcomes.values() if v == "not_found")
    n_error = sum(1 for v in repo_outcomes.values() if v == "error")
    n_skills = sum(1 for r in results if not r.get("fetch_error"))
    hit_rate = round(n_found / n_total, 3) if n_total else 0
    skills_per_hit = round(n_skills / n_found, 1) if n_found else 0
    return {
        "list_id": list_meta.get("list_id", ""),
        "list_source": list_meta.get("source", ""),
        "repos_in_list": n_total,
        "repos_found_skills": n_found,
        "repos_empty": n_empty,
        "repos_not_found": n_not_found,
        "repos_error": n_error,
        "hit_rate": hit_rate,
        "skills_per_hit_repo": skills_per_hit,
        "total_skills": n_skills,
        "outcomes": repo_outcomes,
    }


def process_index_only(repo_name: str, crawl_id: str,
                       all_repos: set[str], dry_run: bool) -> list[str]:
    """Fetch README, extract GitHub links, write discovery queue."""
    candidates: list[str] = []
    for readme in ("README.md", "readme.md", "README"):
        try:
            resp = httpx.get(
                f"https://raw.githubusercontent.com/{repo_name}/HEAD/{readme}",
                timeout=15, follow_redirects=True,
            )
            if resp.status_code == 200:
                links = re.findall(
                    r"https://github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)",
                    resp.text,
                )
                seen: set[str] = set()
                for link in links:
                    link = re.sub(r"[/#\)\]\'\">].*$", "", link)
                    if "/" in link and link not in all_repos and link != repo_name and link not in seen:
                        seen.add(link)
                        candidates.append(link)
                break
        except httpx.RequestError:
            continue

    console.print(f"    → [cyan]{len(candidates)}[/cyan] new candidate(s)")
    if not dry_run and candidates:
        DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
        out = DISCOVERY_DIR / f"{crawl_id}-from-{repo_name.replace('/', '_')}.json"
        out.write_text(json.dumps({
            "crawl_id": crawl_id,
            "source_repo": repo_name,
            "discovered": [{"repo": r, "status": "pending"} for r in candidates],
        }, indent=2))
    return candidates


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Local crawl — reads SKILL.md files from a local directory tree
# ---------------------------------------------------------------------------

@app.command()
def local(
    path: Path = typer.Argument(..., help="Root directory to scan (e.g. ~/.claude/skills/)"),
    org: str = typer.Option("local", "--org", help="Org/author label to assign to discovered skills"),
    out: Optional[Path] = typer.Option(None, "--out", help="Output JSON file (default: crawls/local-<date>.json)"),
):
    """Crawl a local directory tree for SKILL.md files and emit a skill JSON file."""
    path = path.expanduser().resolve()
    if not path.exists():
        console.print(f"[red]Path does not exist: {path}[/red]")
        raise typer.Exit(1)

    crawl_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = out or (BASE_DIR / "crawls" / f"local-{crawl_date}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    skill_files = list(path.rglob("SKILL.md")) + list(path.rglob("skill.md"))
    console.print(f"Found [bold]{len(skill_files)}[/bold] SKILL.md files under {path}")

    for sf in skill_files:
        content = sf.read_text(errors="replace")
        # Extract title from first # heading
        title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        label = title_match.group(1).strip() if title_match else sf.parent.name
        # Extract description from first paragraph after heading
        desc_match = re.search(r'^#[^\n]*\n+([^#\n][^\n]+)', content, re.MULTILINE)
        description = desc_match.group(1).strip() if desc_match else ""
        skill_id = f"{org}/{sf.parent.name}"
        results.append({
            "id": skill_id,
            "label": sf.parent.name,
            "org": org,
            "description": description,
            "skill_md_url": str(sf),
            "repo_url": str(sf.parent),
            "crawl_date": crawl_date,
            "source": "local",
        })
        console.print(f"  [green]✓[/green] {skill_id} — {description[:60]}")

    out_path.write_text(json.dumps(results, indent=2))
    console.print(f"\n[bold green]Done.[/bold green] {len(results)} skills → {out_path}")
    console.print("\n[dim]To add these to the map, run:[/dim]")
    console.print(f"  [cyan]python crawlers/build_graph.py --include {out_path}[/cyan]")


# CLI
# ---------------------------------------------------------------------------

@app.command()
def crawl(
    crawl_list: Optional[Path] = typer.Option(None, "--crawl-list", help="JSON crawl-list file for repo-scoped mode."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Search/plan only — no fetches, writes, or commits."),
):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print("[red]Error: GITHUB_TOKEN is not set.[/red]")
        raise typer.Exit(1)

    gh = make_gh(token)
    crawl_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    existing_dir = find_today_dir(crawl_date)
    if existing_dir:
        crawl_id = existing_dir.name
        crawl_dir = existing_dir
        console.print(f"[yellow]Resuming[/yellow] existing crawl: [bold]{crawl_id}[/bold]")
    else:
        n = next_crawl_n()
        crawl_id = f"crawl-{n}-{crawl_date}"
        crawl_dir = CRAWLS_DIR / crawl_id
        crawl_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]Starting[/green] new crawl: [bold]{crawl_id}[/bold]")

    if dry_run:
        console.print("\n[bold yellow]── DRY RUN ──[/bold yellow]")

    # -----------------------------------------------------------------------
    # Discovery phase
    # -----------------------------------------------------------------------
    console.rule("Discovery")

    # raw_items: (repo_full_name, file_path, file_sha, raw_url, repo_url, repo_type)
    raw_items: list[tuple] = []
    seen_keys: set[str] = set()
    queries_run: list[str] = []

    repo_outcomes: dict[str, str] = {}
    list_meta: dict = {}

    if crawl_list:
        entries, list_meta = load_crawl_list(crawl_list)
        all_repos = {e["repo"] for e in entries}
        console.print(f"Mode: [bold]repo-scoped[/bold] — {len(entries)} entries from [cyan]{crawl_list.name}[/cyan]")

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as prog:
            task = prog.add_task("Scanning repos…", total=len(entries))
            for entry in entries:
                repo_name = entry["repo"]
                repo_type = entry.get("type", "domain-collection")
                prog.update(task, description=f"[dim]{repo_name}[/dim] [{repo_type}]")

                if repo_type == "index-only":
                    process_index_only(repo_name, crawl_id, all_repos, dry_run)
                    repo_outcomes[repo_name] = "index-only"
                    prog.advance(task)
                    time.sleep(0.3)
                    continue

                try:
                    found = walk_repo_tree(gh, repo_name)
                except GithubException as e:
                    status_code = getattr(e, "status", 0)
                    repo_outcomes[repo_name] = "not_found" if status_code == 404 else "error"
                    console.print(f"  [red]Error scanning {repo_name}: {e}[/red]")
                    prog.advance(task)
                    continue

                new = gemini_count = 0
                for f in found:
                    key = f"{f['repo_full_name']}::{f['file_path']}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        raw_items.append((
                            f["repo_full_name"], f["file_path"], f["file_sha"],
                            f["file_raw_url"], f["repo_url"], repo_type,
                            f.get("file_format", "claude"),
                        ))
                        new += 1
                        if f.get("file_format") == "gemini":
                            gemini_count += 1
                repo_outcomes[repo_name] = "found" if found else "empty"
                gemini_note = f" ([yellow]{gemini_count} gemini[/yellow])" if gemini_count else ""
                console.print(f"  [dim]{repo_name}[/dim] [{repo_type}] → [cyan]{new}[/cyan] SKILL.md file(s){gemini_note}")
                prog.advance(task)
                time.sleep(0.3)

        queries_run = [f"crawl-list:{crawl_list.name}"]

    else:
        # Global search via PyGithub
        console.print("Mode: [bold]global search[/bold]")
        for query in GLOBAL_QUERIES:
            console.print(f"  Query: [cyan]{query}[/cyan]")
            try:
                page = 0
                while True:
                    wait_for_rate_limit(gh, "search")
                    items = search_code_page(gh, query, page)
                    if not items:
                        break
                    new = 0
                    for item in items:
                        repo_full_name = item.repository.full_name
                        file_path = item.path
                        key = f"{repo_full_name}::{file_path}"
                        if key not in seen_keys:
                            seen_keys.add(key)
                            raw_url = f"https://raw.githubusercontent.com/{repo_full_name}/HEAD/{file_path}"
                            raw_items.append((
                                repo_full_name, file_path, "",
                                raw_url, item.repository.html_url, "search", "claude",
                            ))
                            new += 1
                    console.print(f"    page {page}: {new} new ({len(raw_items)} total)")
                    if len(items) < 100:
                        break
                    page += 1
                    time.sleep(1)
            except GithubException as e:
                console.print(f"  [red]Search error: {e}[/red]")
            queries_run.append(query)

    if dry_run:
        claude_count = sum(1 for *_, fmt in raw_items if fmt == "claude")
        gemini_count = sum(1 for *_, fmt in raw_items if fmt == "gemini")
        table = Table("Repo", "Type", "Format", "File",
                      title=f"Would fetch {claude_count} claude + {gemini_count} gemini (no-fetch) = {len(raw_items)} total")
        for repo_full_name, file_path, sha, _, _, rtype, fmt in raw_items:
            table.add_row(repo_full_name, rtype, fmt, file_path)
        console.print(table)
        return

    # -----------------------------------------------------------------------
    # Fetch phase
    # -----------------------------------------------------------------------
    console.rule("Fetching")

    results, sha_map = load_existing(crawl_dir)
    result_index: dict[str, int] = {
        f"{r['repo_full_name']}::{r['file_path']}": i for i, r in enumerate(results)
    }
    errors = sum(1 for r in results if r.get("fetch_error"))

    # Cache repo meta per-repo so we don't re-fetch for every file in the same repo
    repo_meta_cache: dict[str, dict] = {}

    def handle_interrupt(sig, frame):
        console.print("\n[yellow]Interrupted — saving state…[/yellow]")
        write_data(crawl_dir, crawl_id, crawl_date, results, queries_run)
        quality = input_quality_metrics(list_meta, repo_outcomes, results) if list_meta else None
        write_meta(crawl_dir, crawl_id, crawl_date, "interrupted", results, errors, queries_run, quality)
        sys.exit(1)

    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    write_meta(crawl_dir, crawl_id, crawl_date, "running", results, errors, queries_run)

    skipped = fetched = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as prog:
        task = prog.add_task("Fetching…", total=len(raw_items))

        for repo_full_name, file_path, file_sha, raw_url, repo_url, repo_type, file_format in raw_items:
            key = f"{repo_full_name}::{file_path}"
            is_canonical = repo_type == "canonical"
            is_gemini = file_format == "gemini"

            # SHA-diff skip — bypass for canonical
            if not is_canonical and key in sha_map and sha_map[key] == file_sha and file_sha:
                skipped += 1
                prog.advance(task)
                continue

            prog.update(task, description=f"[dim]{repo_full_name}[/dim] / {Path(file_path).parent}")

            result: dict = {
                "repo_full_name": repo_full_name,
                "repo_url": repo_url,
                "repo_source": repo_type,
                "file_format": file_format,
                "repo_description": "",
                "repo_stars": 0,
                "repo_forks": 0,
                "repo_topics": [],
                "repo_last_pushed": "",
                "repo_owner_type": "",
                "file_path": file_path,
                "file_sha": file_sha,
                "file_raw_url": raw_url,
                "skill_md_content": None if is_gemini else "",
                "fetch_error": None,
            }

            # Repo meta — cached per repo, re-fetched for canonical
            if is_canonical or repo_full_name not in repo_meta_cache:
                try:
                    repo_meta_cache[repo_full_name] = get_repo_meta(gh, repo_full_name)
                except GithubException as e:
                    result["fetch_error"] = f"repo_meta: {e}"
                    errors += 1
                    upsert(results, result_index, result)
                    write_data(crawl_dir, crawl_id, crawl_date, results, queries_run)
                    write_meta(crawl_dir, crawl_id, crawl_date, "running", results, errors, queries_run)
                    prog.advance(task)
                    continue
            result.update(repo_meta_cache[repo_full_name])

            # Raw file fetch — skip for gemini-format files (content irrelevant for now)
            if is_gemini:
                fetched += 1
            else:
                time.sleep(0.1)
                try:
                    content, error = fetch_raw(raw_url)
                    if error:
                        result["fetch_error"] = f"file_content: {error}"
                        errors += 1
                    else:
                        result["skill_md_content"] = content
                        fetched += 1
                except Exception as e:
                    result["fetch_error"] = f"file_content: {e}"
                    errors += 1

            upsert(results, result_index, result)
            write_data(crawl_dir, crawl_id, crawl_date, results, queries_run)
            write_meta(crawl_dir, crawl_id, crawl_date, "running", results, errors, queries_run)
            prog.advance(task)

    # -----------------------------------------------------------------------
    # Finalise
    # -----------------------------------------------------------------------
    quality = input_quality_metrics(list_meta, repo_outcomes, results) if list_meta else None
    write_data(crawl_dir, crawl_id, crawl_date, results, queries_run)
    write_meta(crawl_dir, crawl_id, crawl_date, "complete", results, errors, queries_run, quality)
    write_summary(crawl_dir, crawl_id, crawl_date, results, errors, queries_run)

    unique_repos = len({r["repo_full_name"] for r in results})
    skills_found = sum(1 for r in results if not r.get("fetch_error"))

    table = Table(title=f"✓ Crawl complete: {crawl_id}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Repos", str(unique_repos))
    table.add_row("Skills found", str(skills_found))
    table.add_row("Fetched (new/changed)", str(fetched))
    table.add_row("Skipped (unchanged SHA)", str(skipped))
    table.add_row("Errors", str(errors))
    if quality:
        table.add_row("Hit rate", f"{quality['hit_rate']:.0%} ({quality['repos_found_skills']}/{quality['repos_in_list']} repos)")
        table.add_row("Skills per hit repo", str(quality["skills_per_hit_repo"]))
    table.add_row("Output", str(crawl_dir))
    console.print(table)

    git_commit_push(crawl_id)


if __name__ == "__main__":
    app()
