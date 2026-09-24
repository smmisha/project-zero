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


def _changes_per_commit(repo_path: str, days: int) -> List[Tuple[str, List[str]]]:
    """
    Return [(author, [path, ...]), ...] for each commit in the last N days,
    newest first, with every path resolved to the file's *current* name.

    Renames are followed: when a commit renames old -> new, older commits
    that touched `old` are credited to `new` (and on through later renames).
    A path reused after a rename is a separate file, because commits newer
    than the rename are resolved before the mapping is recorded.
    """
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    output = _run_git(
        ["-c", "core.quotepath=off", "log", f"--since={since}", "-M",
         "--format=COMMIT:%an", "--name-status", "--diff-filter=ACDMR"],
        repo_path,
    )

    renamed_to: Dict[str, str] = {}

    def resolve(path: str) -> str:
        seen = set()
        while path in renamed_to and path not in seen:
            seen.add(path)
            path = renamed_to[path]
        return path

    commits: List[Tuple[str, List[str]]] = []
    for line in output.splitlines():
        if line.startswith("COMMIT:"):
            commits.append((line[7:].strip(), []))
            continue
        if not line.strip() or not commits:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) == 3:
            old, new = parts[1], parts[2]
            current = resolve(new)
            renamed_to[old] = current
            commits[-1][1].append(current)
        elif status.startswith("C") and len(parts) == 3:
            commits[-1][1].append(resolve(parts[2]))
        elif len(parts) >= 2:
            commits[-1][1].append(resolve(parts[-1]))
    return commits


def get_file_churn(repo_path: str, days: int = 90) -> Dict[str, int]:
    """Count commits per file over the last N days (following renames)."""
    churn: Dict[str, int] = defaultdict(int)
    for _author, paths in _changes_per_commit(repo_path, days):
        for path in set(paths):
            churn[path] += 1
    return dict(churn)


def get_commit_count(repo_path: str, days: int = 90) -> int:
    """Number of commits in the last N days."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    output = _run_git(["rev-list", "--count", f"--since={since}", "HEAD"], repo_path)
    try:
        return int(output.strip())
    except ValueError:
        return 0


def get_authors_per_file(repo_path: str, days: int = 90) -> Dict[str, List[str]]:
    """Returns {filepath: [author1, author2, ...]}, following renames."""
    authors_per_file: Dict[str, set] = defaultdict(set)
    for author, paths in _changes_per_commit(repo_path, days):
        for path in paths:
            authors_per_file[path].add(author)
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
    # Case-sensitive on purpose: "todo" or "bug" in ordinary prose is not a
    # debt marker. NOTE is excluded because it documents, it doesn't defer.
    todo_pattern = re.compile(
        r"\b(TODO|FIXME|HACK|XXX|BUG|KLUDGE|OPTIMIZE)\b[\s:]*(.{0,100})"
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
