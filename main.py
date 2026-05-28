#!/usr/bin/env python3
"""
git-hotspots: Find the riskiest files in your codebase.

Combines git churn history with code complexity to surface files
that are both frequently changed AND hard to understand —
the most likely sources of bugs and the best candidates for refactoring.

Usage:
    python main.py [repo_path] [options]
    python main.py /path/to/repo --days 60 --top 15 --html report.html
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
from git_hotspots.hotspots import calculate_hotspots, get_summary_stats
from git_hotspots.reporter import (
    print_header,
    print_summary,
    print_hotspots_table,
    print_todos_table,
    print_commit_heatmap,
    print_quadrant_legend,
    generate_html_report,
    CYAN, BOLD, RESET, DIM,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="git-hotspots: Codebase risk intelligence via churn × complexity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # analyze current directory
  python main.py /path/to/repo           # analyze specific repo
  python main.py --days 30 --top 20      # last 30 days, show top 20
  python main.py --html report.html      # also generate HTML report
  python main.py --no-todos              # skip TODO debt analysis (faster)
  python main.py --json                  # output JSON for scripting
        """,
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to git repository (default: current directory)",
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
        help="Generate interactive HTML report at FILE",
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
    return parser.parse_args()


def _progress(msg: str) -> None:
    print(f"{DIM}  ⟳  {msg}...{RESET}", end="\r", flush=True)


def _clear_progress() -> None:
    print(" " * 60, end="\r")


def main():
    args = parse_args()

    # Resolve repo path
    repo_path = os.path.abspath(args.repo)
    if not os.path.isdir(repo_path):
        print(f"Error: '{repo_path}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    git_root = get_repo_root(repo_path)
    if not git_root or not os.path.isdir(os.path.join(git_root, ".git")):
        print(f"Error: '{repo_path}' is not inside a git repository.", file=sys.stderr)
        sys.exit(1)

    if not args.json:
        print_header(args.days, git_root)

    # ── Step 1: Git analysis ───────────────────────────────────────────────
    _progress("Analyzing git history")
    churn = get_file_churn(git_root, days=args.days)
    authors = get_authors_per_file(git_root, days=args.days)
    heatmap = get_commit_heatmap(git_root, days=args.days)
    hours = get_hourly_distribution(git_root, days=args.days)
    _clear_progress()

    if not churn:
        print(f"  No commits found in the last {args.days} days.")
        sys.exit(0)

    # Filter by min-churn
    if args.min_churn > 1:
        churn = {f: c for f, c in churn.items() if c >= args.min_churn}

    # ── Step 2: Complexity analysis ────────────────────────────────────────
    _progress("Measuring code complexity")
    tracked_files = list(churn.keys())
    complexity = scan_repository(git_root, tracked_files=tracked_files)
    _clear_progress()

    # ── Step 3: Calculate hotspots ─────────────────────────────────────────
    _progress("Calculating hotspot scores")
    hotspots = calculate_hotspots(churn, complexity, authors, top_n=args.top)
    stats = get_summary_stats(hotspots, churn, complexity)
    _clear_progress()

    # ── Step 4: TODO debt ──────────────────────────────────────────────────
    todos = []
    if not args.no_todos:
        # Only blame files that are hotspots (for speed)
        blame_targets = [h["file"] for h in hotspots[:10]]
        if blame_targets:
            _progress("Finding TODO debt in top hotspots")
            todos = find_todos_with_blame(git_root, blame_targets)
            _clear_progress()

    # ── Output ─────────────────────────────────────────────────────────────
    if args.json:
        import json
        output = {
            "repo": git_root,
            "days": args.days,
            "stats": stats,
            "hotspots": hotspots,
            "todos": todos,
        }
        print(json.dumps(output, indent=2))
        return

    print_summary(stats)
    print_hotspots_table(hotspots)

    if todos:
        print_todos_table(todos)

    if heatmap:
        print_commit_heatmap(heatmap, args.days)

    print_quadrant_legend()

    if args.html:
        _progress(f"Generating HTML report → {args.html}")
        generate_html_report(
            hotspots=hotspots,
            todos=todos,
            stats=stats,
            heatmap=heatmap,
            hours=hours,
            repo_path=git_root,
            days=args.days,
            output_path=args.html,
        )
        _clear_progress()
        print(f"  {BOLD}{CYAN}HTML report saved → {args.html}{RESET}")
        print()


if __name__ == "__main__":
    main()
