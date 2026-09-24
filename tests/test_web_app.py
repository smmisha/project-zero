import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import web_app  # noqa: E402

client = TestClient(web_app.app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "https://evil.example.com/a/b",
    "https://github.com/a",
    "https://github.com/-upload-pack/x;rm",
])
def test_rejects_non_repo_urls(url):
    body = client.post("/analyze-stream", data={"url": url}).text
    assert "Only GitHub, GitLab, or Bitbucket HTTPS URLs are accepted." in body


def test_parse_exclude():
    assert web_app._parse_exclude(" tests, ,*.min.js ") == ["tests", "*.min.js"]
    assert web_app._parse_exclude("") == []


def test_unknown_report_is_404():
    assert client.get("/report/" + "0" * 32).status_code == 404
    assert client.get("/report/../../etc/passwd").status_code == 404
