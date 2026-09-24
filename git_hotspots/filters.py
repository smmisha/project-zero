"""Path filtering for --exclude patterns."""
import fnmatch
from typing import Dict, Iterable, List, Optional, TypeVar

T = TypeVar("T")


def is_excluded(path: str, patterns: Optional[Iterable[str]]) -> bool:
    """
    Return True if `path` matches any exclude pattern.

    A pattern with glob characters (*, ?, [) is matched with fnmatch against
    the full path. A plain pattern like "tests" or "tests/" excludes that
    directory at any depth, or that exact file.
    """
    if not patterns:
        return False
    path = path.replace("\\", "/")
    parts = path.split("/")
    for pattern in patterns:
        pattern = pattern.strip().replace("\\", "/")
        if not pattern:
            continue
        if any(ch in pattern for ch in "*?["):
            if fnmatch.fnmatch(path, pattern):
                return True
            continue
        pattern = pattern.strip("/")
        if path == pattern or path.startswith(pattern + "/"):
            return True
        if "/" not in pattern and pattern in parts[:-1]:
            return True
    return False


def filter_paths(data: Dict[str, T], patterns: Optional[List[str]]) -> Dict[str, T]:
    """Drop keys of a {path: value} dict that match any exclude pattern."""
    if not patterns:
        return data
    return {p: v for p, v in data.items() if not is_excluded(p, patterns)}
