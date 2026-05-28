"""Language-agnostic code complexity analysis using heuristics."""
import os
import re
from typing import Dict, Optional

# Branch keywords per language family
_BRANCH_KEYWORDS = {
    "python": [
        r"\bif\b", r"\belif\b", r"\bfor\b", r"\bwhile\b",
        r"\bexcept\b", r"\bwith\b", r"\band\b", r"\bor\b",
        r"\bassert\b", r"\blambda\b",
    ],
    "js_ts": [
        r"\bif\b", r"\belse\b", r"\bfor\b", r"\bwhile\b",
        r"\bswitch\b", r"\bcase\b", r"\bcatch\b", r"\b\?\.",
        r"\?\?", r"\?\s*:",
    ],
    "java_kotlin": [
        r"\bif\b", r"\bfor\b", r"\bwhile\b", r"\bswitch\b",
        r"\bcase\b", r"\bcatch\b", r"\bthrow\b", r"\binstanceof\b",
    ],
    "go": [
        r"\bif\b", r"\bfor\b", r"\bswitch\b", r"\bcase\b",
        r"\bselect\b", r"\bdefer\b", r"\bgo\b",
    ],
    "rust": [
        r"\bif\b", r"\bfor\b", r"\bwhile\b", r"\bmatch\b",
        r"\b\?\b", r"\bunwrap\b", r"\bexpect\b",
    ],
    "c_cpp": [
        r"\bif\b", r"\bfor\b", r"\bwhile\b", r"\bswitch\b",
        r"\bcase\b", r"\bgoto\b",
    ],
    "generic": [
        r"\bif\b", r"\bfor\b", r"\bwhile\b", r"\bswitch\b",
        r"\bcase\b", r"\bcatch\b",
    ],
}

_FUNCTION_PATTERNS = {
    "python": [r"^\s*def\s+\w+", r"^\s*async\s+def\s+\w+"],
    "js_ts": [
        r"function\s+\w+\s*\(",
        r"^\s*\w+\s*:\s*(?:async\s+)?\(",
        r"=>\s*[{(]",
        r"^\s*(?:async\s+)?(?:get|set)\s+\w+",
    ],
    "java_kotlin": [
        r"(?:public|private|protected|internal|override)\s+(?:\w+\s+)+\w+\s*\(",
        r"^\s*fun\s+\w+",
    ],
    "go": [r"^\s*func\s+(?:\(\w+\s+\*?\w+\)\s+)?\w+"],
    "rust": [r"^\s*(?:pub\s+)?fn\s+\w+"],
    "c_cpp": [r"^\s*\w[\w\s\*]+\s+\w+\s*\("],
    "generic": [r"^\s*(?:def|func|function)\s+\w+"],
}

_EXTENSION_MAP = {
    ".py": "python",
    ".js": "js_ts", ".jsx": "js_ts", ".ts": "js_ts", ".tsx": "js_ts",
    ".java": "java_kotlin", ".kt": "java_kotlin", ".kts": "java_kotlin",
    ".go": "go",
    ".rs": "rust",
    ".c": "c_cpp", ".cpp": "c_cpp", ".cc": "c_cpp", ".h": "c_cpp", ".hpp": "c_cpp",
    ".rb": "generic", ".php": "generic", ".swift": "generic",
    ".scala": "java_kotlin", ".cs": "java_kotlin",
    ".dart": "js_ts",
}

_SUPPORTED_EXTENSIONS = set(_EXTENSION_MAP.keys())


def _detect_language(filepath: str) -> Optional[str]:
    _, ext = os.path.splitext(filepath.lower())
    return _EXTENSION_MAP.get(ext)


def analyze_file(filepath: str) -> Optional[Dict]:
    """
    Analyze a single file and return complexity metrics.
    Returns None if the file is binary, too large, or unsupported.
    """
    lang = _detect_language(filepath)
    if lang is None:
        return None

    try:
        size = os.path.getsize(filepath)
        if size > 500_000:  # skip huge files
            return None
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except (IOError, OSError):
        return None

    if not lines:
        return None

    # Lines of code (non-empty, non-pure-comment)
    code_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "//", "*", "/*", "*/", "'")):
            code_lines.append(line)

    loc = len(code_lines)
    if loc == 0:
        return None

    # Branch count
    branch_patterns = [re.compile(p) for p in _BRANCH_KEYWORDS.get(lang, _BRANCH_KEYWORDS["generic"])]
    branch_count = 0
    for line in code_lines:
        for pattern in branch_patterns:
            branch_count += len(pattern.findall(line))

    # Function count
    func_patterns = [re.compile(p, re.MULTILINE) for p in _FUNCTION_PATTERNS.get(lang, _FUNCTION_PATTERNS["generic"])]
    func_count = 0
    full_text = "".join(lines)
    for pattern in func_patterns:
        func_count += len(pattern.findall(full_text))

    # Max nesting depth (indentation-based)
    indent_depths = []
    for line in code_lines:
        if not line.strip():
            continue
        spaces = len(line) - len(line.lstrip())
        # Normalize: 4 spaces or 1 tab = 1 level
        if line[0] == "\t":
            depth = spaces
        else:
            depth = spaces // 4
        indent_depths.append(depth)

    max_depth = max(indent_depths) if indent_depths else 0

    # Raw complexity: Halstead-inspired heuristic
    # branches contribute most, then functions and depth
    raw_complexity = branch_count + (func_count * 2) + (max_depth * 1.5)

    # Normalize: complexity per 100 LOC, capped at 100
    complexity_score = min(100.0, (raw_complexity / max(loc, 1)) * 100)

    return {
        "loc": loc,
        "branch_count": branch_count,
        "function_count": func_count,
        "max_depth": max_depth,
        "complexity_score": round(complexity_score, 2),
        "language": lang,
    }


def scan_repository(repo_path: str, tracked_files: Optional[list] = None) -> Dict[str, Dict]:
    """
    Scan all source files in the repository.
    If tracked_files is provided, only analyze those files.
    Returns {filepath: metrics_dict}.
    """
    results = {}

    if tracked_files is not None:
        candidates = tracked_files
    else:
        candidates = []
        for root, dirs, files in os.walk(repo_path):
            # Skip common non-source directories
            dirs[:] = [
                d for d in dirs
                if d not in {
                    ".git", "node_modules", "__pycache__", ".venv", "venv",
                    "env", "dist", "build", "target", ".next", ".nuxt",
                    "vendor", "third_party", ".cache", "coverage",
                }
            ]
            for fname in files:
                _, ext = os.path.splitext(fname.lower())
                if ext in _SUPPORTED_EXTENSIONS:
                    candidates.append(os.path.join(root, fname))

    for fpath in candidates:
        # Make path relative for display
        full_path = fpath if os.path.isabs(fpath) else os.path.join(repo_path, fpath)
        rel_path = os.path.relpath(full_path, repo_path)

        metrics = analyze_file(full_path)
        if metrics:
            results[rel_path] = metrics

    return results
