"""Git history analysis: churn, authors, commit timeline."""
import subprocess
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


def _run_git(args: list, cwd: str) -> str:
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        errors="replace",
    )
    return result.stdout


def get_file_churn(repo_path: str, days: int = 90) -> Dict[str, int]:
    """Count commits per file over the last N days."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    output = _run_git(
        ["log", f"--since={since}", "--name-only", "--format=", "--diff-filter=ACDMR"],
        repo_path,
    )
    churn: Dict[str, int] = defaultdict(int)
    for line in output.splitlines():
        line = line.strip()
        if line:
            churn[line] += 1
    return dict(churn)


def get_file_authors(repo_path: str, days: int = 90) -> Dict[str, set]:
    """Return set of unique authors per file."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    output = _run_git(
        ["log", f"--since={since}", "--name-only", "--format=%an", "--diff-filter=ACDMR"],
        repo_path,
    )
    authors: Dict[str, set] = defaultdict(set)
    current_author = None
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        # Lines not containing path separators and not starting with whitespace
        # that follow a blank line are author names
        if current_author is None:
            current_author = line
        elif line:
            authors[line].add(current_author)
            # Next non-empty line after a file path is a new author
    return dict(authors)


def get_authors_per_file(repo_path: str, days: int = 90) -> Dict[str, List[str]]:
    """
    Returns {filepath: [author1, author2, ...]} using git log --follow.
    Uses a single git log call, parsing the interleaved output.
    """
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    output = _run_git(
        ["log", f"--since={since}", "--format=COMMIT:%an", "--name-only", "--diff-filter=ACDMR"],
        repo_path,
    )
    authors_per_file: Dict[str, set] = defaultdict(set)
    current_author = None
    for line in output.splitlines():
        if line.startswith("COMMIT:"):
            current_author = line[7:].strip()
        elif line.strip() and current_author:
            authors_per_file[line.strip()].add(current_author)
    return {f: list(a) for f, a in authors_per_file.items()}


def get_commit_stats(repo_path: str, days: int = 90) -> List[dict]:
    """Return list of commit metadata for the last N days."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    output = _run_git(
        ["log", f"--since={since}", "--format=%H|%an|%ad|%s", "--date=short"],
        repo_path,
    )
    commits = []
    for line in output.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({
                "hash": parts[0][:8],
                "author": parts[1],
                "date": parts[2],
                "subject": parts[3],
            })
    return commits


def get_commit_heatmap(repo_path: str, days: int = 90) -> Dict[str, int]:
    """Returns {YYYY-MM-DD: commit_count} for the period."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    output = _run_git(
        ["log", f"--since={since}", "--format=%ad", "--date=short"],
        repo_path,
    )
    heatmap: Dict[str, int] = defaultdict(int)
    for line in output.splitlines():
        line = line.strip()
        if line:
            heatmap[line] += 1
    return dict(heatmap)


def get_hourly_distribution(repo_path: str, days: int = 90) -> Dict[int, int]:
    """Returns {hour: commit_count} showing when commits happen."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    output = _run_git(
        ["log", f"--since={since}", "--format=%ad", "--date=format:%H"],
        repo_path,
    )
    hours: Dict[int, int] = defaultdict(int)
    for line in output.splitlines():
        line = line.strip()
        if line.isdigit():
            hours[int(line)] += 1
    return dict(hours)


def find_todos_with_blame(repo_path: str, filepaths: List[str]) -> List[dict]:
    """Find TODO/FIXME/HACK/XXX comments and get their age via git blame."""
    todo_pattern = re.compile(
        r"\b(TODO|FIXME|HACK|XXX|NOTE|BUG|KLUDGE|OPTIMIZE)\b[\s:]*(.{0,100})",
        re.IGNORECASE,
    )
    results = []
    for filepath in filepaths:
        try:
            blame_output = _run_git(
                ["blame", "-l", "-w", "--date=short", filepath],
                repo_path,
            )
            for i, line in enumerate(blame_output.splitlines(), 1):
                # git blame format: <hash> (<author> <date> <lineno>) <content>
                match_blame = re.match(
                    r"([0-9a-f]+)\s+\((.+?)\s+(\d{4}-\d{2}-\d{2})\s+\d+\)\s*(.*)",
                    line,
                )
                if not match_blame:
                    continue
                content = match_blame.group(4)
                todo_match = todo_pattern.search(content)
                if todo_match:
                    author = match_blame.group(2).strip()
                    date_str = match_blame.group(3)
                    try:
                        age_days = (datetime.now() - datetime.strptime(date_str, "%Y-%m-%d")).days
                    except ValueError:
                        age_days = 0
                    results.append({
                        "file": filepath,
                        "line": i,
                        "kind": todo_match.group(1).upper(),
                        "text": todo_match.group(2).strip(),
                        "author": author,
                        "date": date_str,
                        "age_days": age_days,
                    })
        except Exception:
            continue
    return results


def get_repo_root(path: str) -> str:
    """Return the git root for the given path."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or path
