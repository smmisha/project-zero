from git_hotspots.filters import filter_paths, is_excluded


def test_plain_name_excludes_directory_at_any_depth():
    assert is_excluded("tests/test_app.py", ["tests"])
    assert is_excluded("pkg/tests/test_app.py", ["tests"])
    assert is_excluded("tests/unit/x.py", ["tests/"])


def test_plain_name_does_not_match_similar_names():
    assert not is_excluded("src/tests_helper.py", ["tests"])
    assert not is_excluded("src/contests/x.py", ["tests"])
    # a bare name only excludes directories, not a file with that name deep in the tree
    assert not is_excluded("src/tests", ["tests"])


def test_path_prefix_and_exact_file():
    assert is_excluded("docs/api/index.py", ["docs/api"])
    assert not is_excluded("src/docs/api/index.py", ["docs/api"])
    assert is_excluded("setup.py", ["setup.py"])


def test_glob_patterns_match_full_path():
    assert is_excluded("static/app.min.js", ["*.min.js"])
    assert is_excluded("docs/conf.py", ["docs/*"])
    assert not is_excluded("src/app.js", ["*.min.js"])


def test_windows_separators_and_empty_patterns():
    assert is_excluded("tests\\test_app.py", ["tests"])
    assert not is_excluded("src/app.py", ["", "  "])
    assert not is_excluded("src/app.py", None)


def test_filter_paths():
    data = {"src/a.py": 3, "tests/test_a.py": 5}
    assert filter_paths(data, ["tests"]) == {"src/a.py": 3}
    assert filter_paths(data, []) is data
