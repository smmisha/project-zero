"""Core hotspot calculation: combines churn and complexity into a risk score."""
import math
from typing import Dict, List


def calculate_hotspots(
    churn: Dict[str, int],
    complexity: Dict[str, dict],
    authors: Dict[str, List[str]],
    top_n: int = 20,
) -> List[dict]:
    """
    Combine churn and complexity into a ranked hotspot list.

    The hotspot score uses the formula from Adam Tornhill's research:
        score = log2(churn + 1) * complexity_score

    Log dampens extreme churn values while preserving ordering.
    """
    all_files = set(churn.keys()) | set(complexity.keys())
    hotspots = []

    for filepath in all_files:
        churn_count = churn.get(filepath, 0)
        comp = complexity.get(filepath, {})
        comp_score = comp.get("complexity_score", 0.0)

        if churn_count == 0 and comp_score == 0:
            continue

        # Normalized churn score (0-100 relative to max)
        raw_score = math.log2(churn_count + 1) * comp_score

        file_authors = authors.get(filepath, [])
        bus_factor = len(set(file_authors))

        hotspots.append({
            "file": filepath,
            "churn": churn_count,
            "complexity": comp_score,
            "loc": comp.get("loc", 0),
            "functions": comp.get("function_count", 0),
            "max_depth": comp.get("max_depth", 0),
            "branches": comp.get("branch_count", 0),
            "language": comp.get("language", "unknown"),
            "bus_factor": bus_factor,
            "authors": list(set(file_authors)),
            "raw_score": raw_score,
        })

    if not hotspots:
        return []

    # Normalize raw_score to 0-100
    max_score = max(h["raw_score"] for h in hotspots) or 1
    for h in hotspots:
        h["score"] = round((h["raw_score"] / max_score) * 100, 1)

    # Sort by score descending
    hotspots.sort(key=lambda x: x["score"], reverse=True)

    return hotspots[:top_n]


def classify_risk(churn_rank: float, complexity_rank: float) -> str:
    """
    Classify a file into one of four quadrants:
    - HIGH churn + HIGH complexity → HOTSPOT (red)
    - HIGH churn + LOW complexity  → REFACTOR CANDIDATE (yellow)
    - LOW churn  + HIGH complexity → LOW RISK (blue)
    - LOW churn  + LOW complexity  → HEALTHY (green)
    """
    high_churn = churn_rank >= 0.5
    high_complexity = complexity_rank >= 0.5

    if high_churn and high_complexity:
        return "HOTSPOT"
    elif high_churn and not high_complexity:
        return "WATCH"
    elif not high_churn and high_complexity:
        return "LOW RISK"
    else:
        return "HEALTHY"


def get_summary_stats(hotspots: List[dict], all_churn: Dict[str, int], all_complexity: Dict[str, dict]) -> dict:
    """Compute summary statistics for the report header."""
    total_files_tracked = len(all_churn)
    total_commits_analyzed = sum(all_churn.values())
    total_files_complex = len(all_complexity)

    hotspot_files = [h for h in hotspots if h["score"] >= 75]

    return {
        "total_files_tracked": total_files_tracked,
        "total_commits_analyzed": total_commits_analyzed,
        "total_files_complex": total_files_complex,
        "hotspot_count": len(hotspot_files),
        "top_file": hotspots[0]["file"] if hotspots else None,
        "top_score": hotspots[0]["score"] if hotspots else 0,
    }
