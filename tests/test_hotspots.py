from git_hotspots.hotspots import calculate_hotspots, compute_risk_index, get_summary_stats


def _complexity(score):
    return {"complexity_score": score, "loc": 10}


def test_score_combines_churn_and_complexity():
    churn = {"hot.py": 15, "complex_stable.py": 1, "busy_simple.py": 15}
    complexity = {
        "hot.py": _complexity(90),
        "complex_stable.py": _complexity(90),
        "busy_simple.py": _complexity(10),
    }
    authors = {"hot.py": ["a"], "complex_stable.py": ["a", "b"]}
    hs = calculate_hotspots(churn, complexity, authors)
    assert [h["file"] for h in hs] == ["hot.py", "complex_stable.py", "busy_simple.py"]
    assert hs[0]["score"] == 100.0
    assert hs[0]["bus_factor"] == 1
    assert hs[2]["bus_factor"] == 0


def test_summary_stats_reports_real_commit_count():
    """Regression: total_commits_analyzed used to be the sum of per-file
    changes, which overcounts whenever a commit touches several files."""
    churn = {"a.py": 3, "b.py": 3}
    hs = calculate_hotspots(churn, {"a.py": _complexity(50)}, {})
    stats = get_summary_stats(hs, churn, {"a.py": _complexity(50)}, commit_count=3)
    assert stats["total_commits_analyzed"] == 3
    assert stats["total_file_changes"] == 6


def test_risk_index_empty_and_tiers():
    assert compute_risk_index([])["risk_index"] == 0.0
    hs = [{"file": "a", "score": 100.0, "bus_factor": 1},
          {"file": "b", "score": 60.0, "bus_factor": 2},
          {"file": "c", "score": 30.0, "bus_factor": 1}]
    r = compute_risk_index(hs)
    assert (r["critical"], r["high"], r["medium"]) == (1, 1, 1)
    assert r["silo_count"] == 2
    assert r["risk_index"] == 145.0
