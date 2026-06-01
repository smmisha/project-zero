#!/usr/bin/env python3
"""
git-hotspots: Find the riskiest files in your codebase.

Combines git churn history with code complexity to surface files
that are both frequently changed AND hard to understand —
the most likely sources of bugs and the best candidates for refactoring.

Usage:
    python main.py [repo_path ...] [options]
    python main.py /path/to/repo --days 60 --top 15 --html report.html
    python main.py repo-a repo-b repo-c        # compare multiple repos
"""

import argparse
import sys
import os

# Allow running as a script from the project directory
sys.path.insert(0, os.path.dirname(__file__))

from git_hotspots.git_analyzer import (
    get_file_churn,
    get_authors_per_file,
    get_commit_heatmap,
    get_hourly_distribution,
    find_todos_with_blame,
    get_repo_root,
)
from git_hotspots.complexity import scan_repository
from git_hotspots.hotspots import calculate_hotspots, get_summary_stats, compute_risk_index
from git_hotspots.reporter import (
    print_header,
    print_summary,
    print_hotspots_table,
    print_todos_table,
    print_commit_heatmap,
    print_quadrant_legend,
    print_multi_repo_header,
    print_repo_comparison,
    print_compact_hotspots,
    generate_html_report,
    CYAN, BOLD, RESET, DIM, RED,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="git-hotspots: Codebase risk intelligence via churn × complexity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # analyze current directory
  python main.py /path/to/repo           # analyze specific repo
  python main.py repo-a repo-b repo-c    # compare multiple repos (portfolio mode)
  python main.py --days 30 --top 20      # last 30 days, show top 20
  python main.py --html report.html      # also generate HTML report
  python main.py --no-todos              # skip TODO debt analysis (faster)
  python main.py --json                  # output JSON for scripting
        """,
    )
    parser.add_argument(
        "repos",
        nargs="*",
        default=["."],
        metavar="REPO",
        help="One or more git repositories (default: current directory). "
             "Passing more than one enables portfolio comparison mode.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        metavar="N",
        help="Analyze last N days of history (default: 90)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        metavar="N",
        help="Show top N hotspots (default: 20)",
    )
    parser.add_argument(
        "--html",
        metavar="FILE",
        help="Generate interactive HTML report at FILE (single-repo mode only)",
    )
    parser.add_argument(
        "--no-todos",
        action="store_true",
        help="Skip TODO debt analysis (faster for large repos)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--min-churn",
        type=int,
        default=1,
        metavar="N",
        help="Minimum churn count to include a file (default: 1)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="In multi-repo mode, show only the comparison ranking "
             "(skip per-repo top hotspots)",
    )
    return parser.parse_args()


def _progress(msg: str) -> None:
    print(f"{DIM}  ⟳  {msg}...{RESET}", end="\r", flush=True)


def _clear_progress() -> None:
    print(" " * 60, end="\r")


def _resolve_git_root(repo_input: str):
    """Validate a repo path and return its git root, or None on failure."""
    repo_path = os.path.abspath(repo_input)
    if not os.path.isdir(repo_path):
        print(f"{RED}Skipping '{repo_input}': not a directory.{RESET}", file=sys.stderr)
        return None
    git_root = get_repo_root(repo_path)
    if not git_root or not os.path.isdir(os.path.join(git_root, ".git")):
        print(f"{RED}Skipping '{repo_input}': not inside a git repository.{RESET}",
              file=sys.stderr)
        return None
    return git_root


def analyze_repo(git_root: str, args, quiet: bool = False) -> dict:
    """
    Run the full analysis pipeline on a single repository.

    Returns a result dict with churn, complexity, hotspots, stats, todos,
    heatmap, hours, and a repo-level risk index. Returns None if the repo
    had no commits in the analysis window.
    """
    def step(msg):
        if not quiet:
            _progress(msg)

    # Git analysis
    step("Analyzing git history")
    churn = get_file_churn(git_root, days=args.days)
    authors = get_authors_per_file(git_root, days=args.days)
    heatmap = get_commit_heatmap(git_root, days=args.days)
    hours = get_hourly_distribution(git_root, days=args.days)
    if not quiet:
        _clear_progress()

    if not churn:
        return None

    if args.min_churn > 1:
        churn = {f: c for f, c in churn.items() if c >= args.min_churn}

    # Complexity analysis
    step("Measuring code complexity")
    tracked_files = list(churn.keys())
    complexity = scan_repository(git_root, tracked_files=tracked_files)
    if not quiet:
        _clear_progress()

    # Hotspot calculation
    step("Calculating hotspot scores")
    hotspots = calculate_hotspots(churn, complexity, authors, top_n=args.top)
    stats = get_summary_stats(hotspots, churn, complexity)
    risk = compute_risk_index(hotspots)
    if not quiet:
        _clear_progress()

    # TODO debt (only top hotspots for speed)
    todos = []
    if not args.no_todos:
        blame_targets = [h["file"] for h in hotspots[:10]]
        if blame_targets:
            step("Finding TODO debt in top hotspots")
            todos = find_todos_with_blame(git_root, blame_targets)
            if not quiet:
                _clear_progress()

    return {
        "git_root": git_root,
        "name": os.path.basename(git_root.rstrip(os.sep)) or git_root,
        "churn": churn,
        "complexity": complexity,
        "hotspots": hotspots,
        "stats": stats,
        "risk": risk,
        "todos": todos,
        "heatmap": heatmap,
        "hours": hours,
        "commits": stats["total_commits_analyzed"],
        "files_measured": stats["total_files_complex"],
    }


def run_single(git_root: str, args) -> int:
    """Single-repo mode: full detailed report."""
    if not args.json:
        print_header(args.days, git_root)

    result = analyze_repo(git_root, args)
    if result is None:
        if args.json:
            import json
            print(json.dumps({"repo": git_root, "days": args.days,
                              "hotspots": [], "todos": []}, indent=2))
        else:
            print(f"  No commits found in the last {args.days} days.")
        return 0

    if args.json:
        import json
        print(json.dumps({
            "repo": git_root,
            "days": args.days,
            "stats": result["stats"],
            "risk": result["risk"],
            "hotspots": result["hotspots"],
            "todos": result["todos"],
        }, indent=2))
        return 0

    print_summary(result["stats"])
    print_hotspots_table(result["hotspots"])
    if result["todos"]:
        print_todos_table(result["todos"])
    if result["heatmap"]:
        print_commit_heatmap(result["heatmap"], args.days)
    print_quadrant_legend()

    if args.html:
        _progress(f"Generating HTML report → {args.html}")
        generate_html_report(
            hotspots=result["hotspots"],
            todos=result["todos"],
            stats=result["stats"],
            heatmap=result["heatmap"],
            hours=result["hours"],
            repo_path=git_root,
            days=args.days,
            output_path=args.html,
        )
        _clear_progress()
        print(f"  {BOLD}{CYAN}HTML report saved → {args.html}{RESET}")
        print()
    return 0


def run_multi(git_roots: list, args) -> int:
    """Portfolio mode: analyze several repos and compare them."""
    results = []
    if not args.json:
        print_multi_repo_header(len(git_roots), args.days)

    for git_root in git_roots:
        name = os.path.basename(git_root.rstrip(os.sep)) or git_root
        if not args.json:
            _progress(f"Analyzing {name}")
        result = analyze_repo(git_root, args, quiet=True)
        if not args.json:
            _clear_progress()
        if result is None:
            if not args.json:
                print(f"  {DIM}{name}: no commits in the last {args.days} days — skipped.{RESET}")
            continue
        results.append(result)

    if not results:
        if args.json:
            import json
            print(json.dumps({"days": args.days, "repos": []}, indent=2))
        else:
            print(f"  No repositories produced any data.")
        return 0

    if args.json:
        import json
        print(json.dumps({
            "days": args.days,
            "repos": [
                {
                    "name": r["name"],
                    "git_root": r["git_root"],
                    "commits": r["commits"],
                    "risk": r["risk"],
                    "stats": r["stats"],
                    "hotspots": r["hotspots"],
                }
                for r in results
            ],
        }, indent=2))
        return 0

    # Comparison table (sorted internally by risk index)
    print_repo_comparison([
        {"name": r["name"], "risk": r["risk"],
         "commits": r["commits"], "files_measured": r["files_measured"]}
        for r in results
    ])

    # Per-repo compact hotspots, riskiest first
    if not args.compact:
        print(f"{BOLD}Per-Repository Top Hotspots{RESET}")
        print()
        for r in sorted(results, key=lambda x: x["risk"]["risk_index"], reverse=True):
            print_compact_hotspots(r["name"], r["hotspots"], limit=5)

    print_quadrant_legend()
    return 0


def main():
    args = parse_args()

    # Resolve and validate every repo path up front
    git_roots = []
    seen = set()
    for repo_input in args.repos:
        git_root = _resolve_git_root(repo_input)
        if git_root and git_root not in seen:
            seen.add(git_root)
            git_roots.append(git_root)

    if not git_roots:
        print("Error: no valid git repositories to analyze.", file=sys.stderr)
        sys.exit(1)

    if len(git_roots) == 1:
        sys.exit(run_single(git_roots[0], args))
    else:
        if args.html:
            print(f"{DIM}  Note: --html is ignored in multi-repo comparison mode.{RESET}",
                  file=sys.stderr)
        sys.exit(run_multi(git_roots, args))


if __name__ == "__main__":
    main()
