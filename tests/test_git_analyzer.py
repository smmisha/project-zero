import os
import subprocess

import pytest

from git_hotspots.git_analyzer import (
    find_todos_with_blame,
    get_authors_per_file,
    get_commit_count,
    get_file_churn,
)


def _git(repo, *args, author="Alice"):
    env = dict(
        os.environ,
        GIT_AUTHOR_NAME=author, GIT_AUTHOR_EMAIL=f"{author}@example.com",
        GIT_COMMITTER_NAME=author, GIT_COMMITTER_EMAIL=f"{author}@example.com",
        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
    )
    subprocess.run(["git", *args], cwd=repo, check=True, env=env,
                   capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "first")                    # touches a, b
    (tmp_path / "a.py").write_text(
        "x = 2\n"
        "# TODO: remove this hack\n"
        "# NOTE: documentation, not debt\n"
        "# the todo list in prose is not a marker\n"
    )
    _git(tmp_path, "commit", "-qam", "second", author="Bob")   # touches a
    return tmp_path


def test_commit_count_is_commits_not_file_changes(repo):
    churn = get_file_churn(str(repo))
    assert churn == {"a.py": 2, "b.py": 1}
    assert sum(churn.values()) == 3
    assert get_commit_count(str(repo)) == 2


def test_authors_per_file(repo):
    authors = get_authors_per_file(str(repo))
    assert sorted(authors["a.py"]) == ["Alice", "Bob"]
    assert authors["b.py"] == ["Alice"]


def test_todos_ignore_note_and_lowercase_prose(repo):
    todos = find_todos_with_blame(str(repo), ["a.py"])
    assert [(t["kind"], t["line"]) for t in todos] == [("TODO", 2)]
    assert todos[0]["text"] == "remove this hack"
    assert todos[0]["author"] == "Bob"


def test_history_follows_renames(tmp_path):
    """A renamed file keeps its history: churn and authors from before the
    rename are credited to the current path, not left on the old one."""
    _git(tmp_path, "init", "-q")
    body = "".join(f"line_{i} = {i}\n" for i in range(30))
    (tmp_path / "old.py").write_text(body)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "create")
    (tmp_path / "old.py").write_text(body + "x = 1\n")
    _git(tmp_path, "commit", "-qam", "edit", author="Bob")
    _git(tmp_path, "mv", "old.py", "mid.py")
    _git(tmp_path, "commit", "-qm", "rename 1")
    _git(tmp_path, "mv", "mid.py", "new.py")
    (tmp_path / "new.py").write_text(body + "x = 2\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "rename 2 + edit", author="Carol")

    assert get_file_churn(str(tmp_path)) == {"new.py": 4}
    assert sorted(get_authors_per_file(str(tmp_path))["new.py"]) == ["Alice", "Bob", "Carol"]


def test_path_reused_after_rename_is_a_separate_file(tmp_path):
    _git(tmp_path, "init", "-q")
    body = "".join(f"line_{i} = {i}\n" for i in range(30))
    (tmp_path / "a.py").write_text(body)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "create a")
    _git(tmp_path, "mv", "a.py", "b.py")
    _git(tmp_path, "commit", "-qm", "rename a -> b")
    (tmp_path / "a.py").write_text("completely = 'different'\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "new file at old path")

    assert get_file_churn(str(tmp_path)) == {"b.py": 2, "a.py": 1}
