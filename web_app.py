#!/usr/bin/env python3
"""
git-hotspots web application.

Accepts a GitHub/GitLab URL, clones the repository, runs the hotspot
analysis, and returns an interactive HTML report — all in the browser.

Run locally:
    uvicorn web_app:app --reload --port 8000

Deploy to Railway / Render / Fly.io:
    set start command to: uvicorn web_app:app --host 0.0.0.0 --port $PORT
"""

import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse

sys.path.insert(0, os.path.dirname(__file__))

from git_hotspots.git_analyzer import (
    get_file_churn,
    get_authors_per_file,
    get_commit_heatmap,
    get_hourly_distribution,
    find_todos_with_blame,
)
from git_hotspots.complexity import scan_repository
from git_hotspots.hotspots import calculate_hotspots, get_summary_stats, compute_risk_index
from git_hotspots.reporter import generate_html_report

# ── Configuration ──────────────────────────────────────────────────────────

CLONE_DEPTH = 200
ANALYSIS_TIMEOUT = 120          # seconds before giving up
ALLOWED_HOSTS_RE = re.compile(
    r"^https://(github\.com|gitlab\.com|bitbucket\.org)/[\w.\-]+/[\w.\-]+(\.git)?$"
)

app = FastAPI(title="git-hotspots", docs_url=None, redoc_url=None)


# ── Helpers ────────────────────────────────────────────────────────────────

def _sanitize_url(url: str) -> str | None:
    """Return the clean URL if it looks like a legit repo, else None."""
    url = url.strip().rstrip("/")
    if not ALLOWED_HOSTS_RE.match(url):
        return None
    return url


def _clone(url: str, dest: str) -> tuple[bool, str]:
    """Shallow-clone a repo. Returns (success, error_message)."""
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", str(CLONE_DEPTH), "--", url, dest],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "git clone timed out (90 s)"
    except Exception as e:
        return False, str(e)


def _run_analysis(repo_path: str, days: int, top: int) -> dict:
    """Run the full pipeline and return a result dict."""
    churn = get_file_churn(repo_path, days=days)
    if not churn:
        return {}
    authors = get_authors_per_file(repo_path, days=days)
    heatmap = get_commit_heatmap(repo_path, days=days)
    hours = get_hourly_distribution(repo_path, days=days)
    complexity = scan_repository(repo_path, tracked_files=list(churn.keys()))
    hotspots = calculate_hotspots(churn, complexity, authors, top_n=top)
    stats = get_summary_stats(hotspots, churn, complexity)
    risk = compute_risk_index(hotspots)
    todos = find_todos_with_blame(repo_path, [h["file"] for h in hotspots[:10]])
    return {
        "hotspots": hotspots,
        "stats": stats,
        "risk": risk,
        "todos": todos,
        "heatmap": heatmap,
        "hours": hours,
    }


# ── Landing page ───────────────────────────────────────────────────────────

LANDING_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>git-hotspots</title>
<style>
  :root {
    --bg: #0f0f13; --card: #1a1a24; --border: #2a2a3a;
    --text: #e2e2f0; --dim: #6b7280;
    --red: #ef4444; --yellow: #f59e0b; --green: #10b981;
    --blue: #06b6d4; --purple: #8b5cf6;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg); color: var(--text);
    font-family: 'Inter', system-ui, sans-serif;
    min-height: 100vh; display: flex; flex-direction: column;
    align-items: center; justify-content: center; padding: 24px;
  }
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 16px; padding: 40px 48px; max-width: 620px; width: 100%;
  }
  h1 { font-size: 2rem; font-weight: 800; color: var(--blue); }
  .tagline { color: var(--dim); margin: 8px 0 32px; font-size: 0.95rem; }
  label { display: block; font-size: 0.8rem; color: var(--dim);
          text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
  input[type=text], input[type=number], select {
    width: 100%; background: #111118; border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); padding: 10px 14px;
    font-size: 0.95rem; outline: none; transition: border-color .15s;
  }
  input[type=text]:focus, input[type=number]:focus {
    border-color: var(--blue);
  }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
  .field { margin-bottom: 0; }
  button {
    margin-top: 24px; width: 100%; padding: 12px;
    background: var(--blue); color: #000; font-weight: 700;
    font-size: 1rem; border: none; border-radius: 8px; cursor: pointer;
    transition: opacity .15s;
  }
  button:hover { opacity: .85; }
  button:disabled { opacity: .4; cursor: not-allowed; }
  #status {
    margin-top: 20px; font-size: 0.85rem; color: var(--dim);
    min-height: 20px; text-align: center;
  }
  #progress-bar {
    margin-top: 10px; height: 3px; background: var(--border); border-radius: 2px;
    overflow: hidden; display: none;
  }
  #progress-fill {
    height: 100%; background: var(--blue); width: 0%;
    transition: width .3s; border-radius: 2px;
  }
  .pills { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 28px; }
  .pill {
    padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 500;
  }
  .pill-red { background: rgba(239,68,68,.12); color: var(--red); }
  .pill-yellow { background: rgba(245,158,11,.12); color: var(--yellow); }
  .pill-green { background: rgba(16,185,129,.12); color: var(--green); }
  .pill-blue { background: rgba(6,182,212,.12); color: var(--blue); }
  footer { margin-top: 24px; color: var(--dim); font-size: 0.78rem; text-align: center; }
  a { color: var(--blue); text-decoration: none; }
</style>
</head>
<body>
<div class="card">
  <h1>git-hotspots</h1>
  <p class="tagline">Find the riskiest files in any GitHub repository — free &amp; local, no API key needed.</p>

  <form id="form">
    <label for="url">Repository URL</label>
    <input type="text" id="url" name="url"
           placeholder="https://github.com/pallets/flask"
           autocomplete="off" required>

    <div class="row">
      <div class="field">
        <label for="days" style="margin-top:16px">Days of history</label>
        <input type="number" id="days" name="days" value="90" min="7" max="730">
      </div>
      <div class="field">
        <label for="top" style="margin-top:16px">Top N files</label>
        <input type="number" id="top" name="top" value="20" min="5" max="50">
      </div>
    </div>

    <button type="submit" id="btn">Analyze →</button>
  </form>

  <div id="status"></div>
  <div id="progress-bar"><div id="progress-fill"></div></div>

  <div class="pills">
    <span class="pill pill-red">Hotspot score</span>
    <span class="pill pill-yellow">Bus factor</span>
    <span class="pill pill-blue">TODO debt age</span>
    <span class="pill pill-green">No cloud / no API key</span>
  </div>
</div>
<footer>
  <a href="https://github.com/smmisha/project-zero" target="_blank">github.com/smmisha/project-zero</a>
  &nbsp;·&nbsp; Inspired by <em>Your Code as a Crime Scene</em> by Adam Tornhill
</footer>

<script>
const form = document.getElementById('form');
const btn  = document.getElementById('btn');
const statusEl = document.getElementById('status');
const bar  = document.getElementById('progress-bar');
const fill = document.getElementById('progress-fill');

const STEPS = ['Cloning repository', 'Analyzing git history', 'Measuring complexity', 'Calculating hotspots', 'Finding TODO debt', 'Generating report'];

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  btn.disabled = true;
  btn.textContent = 'Working…';
  bar.style.display = 'block';
  fill.style.width = '5%';
  statusEl.textContent = '';

  const body = new URLSearchParams({
    url:  document.getElementById('url').value.trim(),
    days: document.getElementById('days').value,
    top:  document.getElementById('top').value,
  });

  const resp = await fetch('/analyze-stream', { method: 'POST', body });

  if (!resp.ok || !resp.body) {
    statusEl.textContent = 'Server error. Try again.';
    btn.disabled = false; btn.textContent = 'Analyze →';
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const data = JSON.parse(line.slice(5).trim());
      if (data.error) {
        statusEl.style.color = '#ef4444';
        statusEl.textContent = '✗  ' + data.error;
        btn.disabled = false; btn.textContent = 'Analyze →';
        fill.style.width = '0';
        return;
      }
      if (data.step !== undefined) {
        const pct = 10 + (data.step / STEPS.length) * 85;
        fill.style.width = pct + '%';
        statusEl.textContent = '⟳  ' + (STEPS[data.step] || '');
      }
      if (data.redirect) {
        fill.style.width = '100%';
        statusEl.textContent = '✓  Done — opening report…';
        setTimeout(() => { window.location.href = data.redirect; }, 400);
        return;
      }
    }
  }
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return LANDING_HTML


# ── Streaming analysis endpoint ────────────────────────────────────────────

async def _analysis_stream(
    url: str, days: int, top: int
) -> AsyncGenerator[str, None]:
    """Yield SSE events describing each analysis step, then a redirect."""

    def event(data: dict) -> str:
        import json
        return f"data: {json.dumps(data)}\n\n"

    clean_url = _sanitize_url(url)
    if not clean_url:
        yield event({"error": "Only GitHub, GitLab, or Bitbucket HTTPS URLs are accepted."})
        return

    tmp_dir = tempfile.mkdtemp(prefix="gh_")
    report_path = None

    try:
        # Step 0 – clone
        yield event({"step": 0})
        ok, err = await asyncio.get_event_loop().run_in_executor(
            None, _clone, clean_url, tmp_dir
        )
        if not ok:
            yield event({"error": f"Clone failed: {err}"})
            return

        # Steps 1-4 – analysis (run in thread executor to avoid blocking)
        yield event({"step": 1})

        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, _run_analysis, tmp_dir, days, top
                ),
                timeout=ANALYSIS_TIMEOUT,
            )
        except asyncio.TimeoutError:
            yield event({"error": f"Analysis timed out after {ANALYSIS_TIMEOUT}s. Try a smaller --days value."})
            return

        if not result:
            yield event({"error": "No commits found in the selected time window."})
            return

        yield event({"step": 2})
        yield event({"step": 3})
        yield event({"step": 4})

        # Step 5 – generate HTML report to a temp file
        yield event({"step": 5})
        job_id = uuid.uuid4().hex
        report_dir = os.path.join(tempfile.gettempdir(), "gh_reports")
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, f"{job_id}.html")

        repo_name = clean_url.rstrip("/").split("/")[-1].removesuffix(".git")

        generate_html_report(
            hotspots=result["hotspots"],
            todos=result["todos"],
            stats=result["stats"],
            heatmap=result["heatmap"],
            hours=result["hours"],
            repo_path=repo_name,
            days=days,
            output_path=report_path,
        )

        yield event({"redirect": f"/report/{job_id}"})

    finally:
        # Always clean up the cloned repo (report stays until served)
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/analyze-stream")
async def analyze_stream(
    url: str = Form(...),
    days: int = Form(90),
    top: int = Form(20),
):
    days = max(7, min(days, 730))
    top  = max(5, min(top, 50))
    return StreamingResponse(
        _analysis_stream(url, days, top),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Report serving ─────────────────────────────────────────────────────────

@app.get("/report/{job_id}", response_class=HTMLResponse)
async def serve_report(job_id: str, background_tasks: BackgroundTasks):
    # Sanitize job_id — hex only
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        return HTMLResponse("Not found", status_code=404)

    report_path = os.path.join(tempfile.gettempdir(), "gh_reports", f"{job_id}.html")
    if not os.path.exists(report_path):
        return HTMLResponse("Report expired or not found.", status_code=404)

    with open(report_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Schedule deletion after serving
    background_tasks.add_task(os.unlink, report_path)
    return HTMLResponse(html)


# ── Health check ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("web_app:app", host="0.0.0.0", port=port, reload=False)
