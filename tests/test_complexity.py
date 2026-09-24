from git_hotspots.complexity import analyze_file, normalize_complexity, scan_repository


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_unsupported_and_empty_files_are_skipped(tmp_path):
    assert analyze_file(_write(tmp_path / "notes.txt", "if x: pass\n")) is None
    assert analyze_file(_write(tmp_path / "empty.py", "# only a comment\n")) is None


def test_analyze_file_counts_branches_and_functions(tmp_path):
    src = (
        "def f(x):\n"
        "    if x and x > 1:\n"
        "        for i in range(x):\n"
        "            pass\n"
        "    return x\n"
    )
    m = analyze_file(_write(tmp_path / "a.py", src))
    assert m["language"] == "python"
    assert m["loc"] == 5
    assert m["function_count"] == 1
    assert m["branch_count"] == 3  # if, and, for
    assert m["max_depth"] == 3
    assert m["raw_complexity"] > 0


def test_bigger_file_outranks_small_dense_file(tmp_path):
    """Regression: the score used to be density per 100 LOC, which ranked a
    3-line file above a 400-line file with the same code style."""
    block = "def f{n}(x):\n    if x:\n        return 1\n    return 0\n"
    _write(tmp_path / "small.py", block.format(n=0))
    _write(tmp_path / "big.py", "".join(block.format(n=i) for i in range(100)))
    results = scan_repository(str(tmp_path))
    assert results["big.py"]["complexity_score"] == 100.0
    assert results["small.py"]["complexity_score"] < 5
    # the old density metric ranked them the other way round
    assert results["small.py"]["density"] > results["big.py"]["density"]


def test_normalize_complexity_handles_empty_input():
    assert normalize_complexity({}) == {}
