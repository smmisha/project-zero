"""Terminal and HTML reporting."""
import os
import json
from datetime import datetime
from typing import List, Dict


# ── ANSI colors (colorama-compatible, works without colorama too) ──────────

try:
    from colorama import init as _cinit, Fore, Style, Back
    _cinit(autoreset=True)
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    GREEN = Fore.GREEN
    CYAN = Fore.CYAN
    BLUE = Fore.BLUE
    MAGENTA = Fore.MAGENTA
    BOLD = Style.BRIGHT
    DIM = Style.DIM
    RESET = Style.RESET_ALL
    BG_RED = Back.RED
    BG_YELLOW = Back.YELLOW
except ImportError:
    RED = YELLOW = GREEN = CYAN = BLUE = MAGENTA = ""
    BOLD = DIM = RESET = BG_RED = BG_YELLOW = ""


def _color_score(score: float) -> str:
    if score >= 75:
        return f"{BOLD}{RED}{score:5.1f}{RESET}"
    elif score >= 50:
        return f"{BOLD}{YELLOW}{score:5.1f}{RESET}"
    elif score >= 25:
        return f"{CYAN}{score:5.1f}{RESET}"
    else:
        return f"{GREEN}{score:5.1f}{RESET}"


def _risk_badge(score: float) -> str:
    if score >= 75:
        return f"{BOLD}{RED}[CRITICAL]{RESET}"
    elif score >= 50:
        return f"{BOLD}{YELLOW}[ HIGH   ]{RESET}"
    elif score >= 25:
        return f"{CYAN}[ MEDIUM ]{RESET}"
    else:
        return f"{GREEN}[  LOW   ]{RESET}"


def _shorten(path: str, max_len: int = 55) -> str:
    if len(path) <= max_len:
        return path
    parts = path.split(os.sep)
    if len(parts) > 3:
        return os.path.join("…", *parts[-2:])
    return "…" + path[-(max_len - 1):]


def print_header(days: int, repo_path: str) -> None:
    width = 72
    print()
    print(f"{BOLD}{CYAN}{'━' * width}{RESET}")
    print(f"{BOLD}{CYAN}  git-hotspots{RESET}  — Codebase Risk Intelligence")
    print(f"{CYAN}{'━' * width}{RESET}")
    print(f"  Repository : {BOLD}{os.path.abspath(repo_path)}{RESET}")
    print(f"  Analysis   : last {BOLD}{days} days{RESET}  ·  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{CYAN}{'━' * width}{RESET}")
    print()


def print_summary(stats: dict) -> None:
    print(f"{BOLD}Summary{RESET}")
    print(f"  Files changed (git) : {BOLD}{stats['total_files_tracked']}{RESET}")
    print(f"  Commits analyzed    : {BOLD}{stats['total_commits_analyzed']}{RESET}")
    print(f"  Files measured      : {BOLD}{stats['total_files_complex']}{RESET}")
    print(f"  Critical hotspots   : {BOLD}{RED}{stats['hotspot_count']}{RESET}")
    print()


def print_hotspots_table(hotspots: List[dict]) -> None:
    if not hotspots:
        print(f"{GREEN}No hotspots found. Your codebase looks healthy!{RESET}")
        return

    col_file = 55
    print(f"{BOLD}Top Hotspots  (score = log₂(churn+1) × complexity){RESET}")
    print(f"{DIM}{'#':>3}  {'RISK':<11}  {'Score':>5}  {'Churn':>5}  {'Cmplx':>5}  "
          f"{'LOC':>5}  {'Bus':>3}  {'File'}{RESET}")
    print(f"{DIM}{'─'*3}  {'─'*9}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*3}  {'─'*col_file}{RESET}")

    for i, h in enumerate(hotspots, 1):
        badge = _risk_badge(h["score"])
        score_str = _color_score(h["score"])
        bus = h["bus_factor"]
        bus_str = f"{RED}{bus}{RESET}" if bus == 1 else f"{YELLOW}{bus}{RESET}" if bus <= 2 else f"{GREEN}{bus}{RESET}"
        file_display = _shorten(h["file"], col_file)
        print(
            f"{i:>3}  {badge}  {score_str}  {h['churn']:>5}  {h['complexity']:>5.1f}  "
            f"{h['loc']:>5}  {bus_str}  {file_display}"
        )
    print()


def print_todos_table(todos: List[dict], max_show: int = 20) -> None:
    if not todos:
        print(f"{GREEN}No TODO/FIXME debt found.{RESET}")
        return

    # Sort by age descending (oldest first)
    sorted_todos = sorted(todos, key=lambda x: x["age_days"], reverse=True)[:max_show]

    print(f"{BOLD}TODO Debt  (oldest first){RESET}  — {len(todos)} total")
    print(f"{DIM}{'Age':>6}  {'Kind':<7}  {'Author':<18}  {'File:Line':<40}  Text{RESET}")
    print(f"{DIM}{'─'*6}  {'─'*7}  {'─'*18}  {'─'*40}  {'─'*40}{RESET}")

    for t in sorted_todos:
        age = t["age_days"]
        age_color = RED if age > 365 else YELLOW if age > 90 else CYAN
        age_str = f"{age_color}{age:>4}d{RESET}"
        kind_color = RED if t["kind"] in ("FIXME", "BUG", "HACK") else YELLOW
        kind_str = f"{kind_color}{t['kind']:<7}{RESET}"
        author = t["author"][:18]
        loc = f"{_shorten(t['file'], 30)}:{t['line']}"
        text = t["text"][:50]
        print(f"{age_str}  {kind_str}  {author:<18}  {loc:<40}  {text}")
    print()


def print_quadrant_legend() -> None:
    print(f"{BOLD}Risk Quadrant Guide{RESET}")
    print(f"  {BOLD}{RED}[CRITICAL]{RESET}  score ≥ 75  →  High churn + High complexity. Refactor NOW.")
    print(f"  {BOLD}{YELLOW}[ HIGH   ]{RESET}  score ≥ 50  →  Actively changing, needs attention.")
    print(f"  {CYAN}[ MEDIUM ]{RESET}  score ≥ 25  →  Monitor. Complexity growing.")
    print(f"  {GREEN}[  LOW   ]{RESET}  score < 25  →  Stable and simple. Keep it this way.")
    print()
    print(f"  {RED}Bus Factor = 1{RESET}  →  Only ONE person understands this file. Knowledge silo risk.")
    print()


def print_commit_heatmap(heatmap: Dict[str, int], days: int) -> None:
    if not heatmap:
        return
    max_count = max(heatmap.values()) if heatmap else 1
    total = sum(heatmap.values())
    print(f"{BOLD}Commit Activity{RESET}  — {total} commits over {days} days")

    # Group by week for display
    from datetime import datetime, timedelta
    today = datetime.now().date()

    blocks = ["░", "▒", "▓", "█"]
    weeks: Dict[str, List] = {}
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i))
        week_key = d.strftime("%Y-W%V")
        if week_key not in weeks:
            weeks[week_key] = []
        count = heatmap.get(d.strftime("%Y-%m-%d"), 0)
        intensity = 0 if count == 0 else 1 + min(2, int((count / max_count) * 3))
        weeks[week_key].append(blocks[intensity])

    line = "  "
    for week_blocks in weeks.values():
        line += "".join(week_blocks) + " "
    print(line)
    print(f"  {DIM}░ = 0  ▒ = low  ▓ = medium  █ = high{RESET}")
    print()


# ── HTML Report ────────────────────────────────────────────────────────────

def generate_html_report(
    hotspots: List[dict],
    todos: List[dict],
    stats: dict,
    heatmap: Dict[str, int],
    hours: Dict[int, int],
    repo_path: str,
    days: int,
    output_path: str,
) -> None:
    """Generate a self-contained HTML report with interactive charts."""

    # Prepare chart data
    top = hotspots[:30]
    scatter_data = json.dumps([
        {"x": h["churn"], "y": round(h["complexity"], 1),
         "r": max(5, min(20, h["loc"] // 50)),
         "label": os.path.basename(h["file"]),
         "full": h["file"],
         "score": h["score"]}
        for h in top
    ])

    bar_labels = json.dumps([os.path.basename(h["file"]) for h in top[:15]])
    bar_scores = json.dumps([h["score"] for h in top[:15]])
    bar_colors = json.dumps([
        "#ef4444" if h["score"] >= 75 else "#f59e0b" if h["score"] >= 50 else "#06b6d4"
        for h in top[:15]
    ])

    heat_labels = json.dumps(sorted(heatmap.keys()))
    heat_values = json.dumps([heatmap[k] for k in sorted(heatmap.keys())])

    hour_labels = json.dumps([f"{h:02d}:00" for h in range(24)])
    hour_values = json.dumps([hours.get(h, 0) for h in range(24)])

    todo_rows = ""
    for t in sorted(todos, key=lambda x: x["age_days"], reverse=True)[:50]:
        age = t["age_days"]
        badge_class = "badge-red" if age > 365 else "badge-yellow" if age > 90 else "badge-blue"
        kind_class = "badge-red" if t["kind"] in ("FIXME", "BUG", "HACK") else "badge-yellow"
        todo_rows += f"""
        <tr>
            <td><span class="badge {badge_class}">{age}d</span></td>
            <td><span class="badge {kind_class}">{t['kind']}</span></td>
            <td class="mono">{t['file']}:{t['line']}</td>
            <td>{t['author'][:20]}</td>
            <td class="text-dim">{t['text'][:80]}</td>
        </tr>"""

    hotspot_rows = ""
    for i, h in enumerate(hotspots[:30], 1):
        score_class = "score-red" if h["score"] >= 75 else "score-yellow" if h["score"] >= 50 else "score-blue"
        bus = h["bus_factor"]
        bus_class = "text-red" if bus == 1 else "text-yellow" if bus <= 2 else "text-green"
        hotspot_rows += f"""
        <tr>
            <td class="text-dim">{i}</td>
            <td class="mono">{h['file']}</td>
            <td class="{score_class}">{h['score']}</td>
            <td>{h['churn']}</td>
            <td>{h['complexity']:.1f}</td>
            <td>{h['loc']}</td>
            <td class="{bus_class}">{bus}</td>
            <td class="text-dim">{h['language']}</td>
        </tr>"""

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    repo_abs = os.path.abspath(repo_path)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>git-hotspots — {os.path.basename(repo_abs)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f0f13;
    --card: #1a1a24;
    --border: #2a2a3a;
    --text: #e2e2f0;
    --dim: #6b7280;
    --red: #ef4444;
    --yellow: #f59e0b;
    --green: #10b981;
    --blue: #06b6d4;
    --purple: #8b5cf6;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Inter', system-ui, sans-serif; padding: 24px; }}
  h1 {{ font-size: 1.8rem; font-weight: 700; color: var(--blue); }}
  h2 {{ font-size: 1.1rem; font-weight: 600; color: var(--text); margin-bottom: 16px; }}
  .subtitle {{ color: var(--dim); font-size: 0.9rem; margin-top: 4px; }}
  .header {{ margin-bottom: 32px; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
  .card-value {{ font-size: 2rem; font-weight: 700; }}
  .card-label {{ color: var(--dim); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }}
  .red {{ color: var(--red); }}
  .yellow {{ color: var(--yellow); }}
  .green {{ color: var(--green); }}
  .blue {{ color: var(--blue); }}
  .charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }}
  .chart-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }}
  .chart-card.full {{ grid-column: 1 / -1; }}
  canvas {{ max-height: 320px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{ color: var(--dim); font-weight: 500; text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #1e1e2a; }}
  tr:hover td {{ background: #1e1e2a; }}
  .mono {{ font-family: 'Fira Code', 'Cascadia Code', monospace; font-size: 0.8rem; color: var(--blue); }}
  .text-dim {{ color: var(--dim); }}
  .text-red {{ color: var(--red); font-weight: 600; }}
  .text-yellow {{ color: var(--yellow); }}
  .text-green {{ color: var(--green); }}
  .score-red {{ color: var(--red); font-weight: 700; }}
  .score-yellow {{ color: var(--yellow); font-weight: 600; }}
  .score-blue {{ color: var(--blue); }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
  .badge-red {{ background: rgba(239,68,68,0.15); color: var(--red); }}
  .badge-yellow {{ background: rgba(245,158,11,0.15); color: var(--yellow); }}
  .badge-blue {{ background: rgba(6,182,212,0.15); color: var(--blue); }}
  .section {{ margin-bottom: 32px; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; overflow-x: auto; }}
  .quadrant-legend {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }}
  .q-item {{ padding: 12px 16px; border-radius: 8px; font-size: 0.85rem; }}
  .q-red {{ background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); }}
  .q-yellow {{ background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); }}
  .q-blue {{ background: rgba(6,182,212,0.1); border: 1px solid rgba(6,182,212,0.3); }}
  .q-green {{ background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); }}
  footer {{ text-align: center; color: var(--dim); font-size: 0.8rem; margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); }}
</style>
</head>
<body>
<div class="header">
  <h1>git-hotspots</h1>
  <div class="subtitle">Codebase Risk Intelligence · {repo_abs} · {now} · last {days} days</div>
</div>

<div class="cards">
  <div class="card">
    <div class="card-value red">{stats['hotspot_count']}</div>
    <div class="card-label">Critical Hotspots</div>
  </div>
  <div class="card">
    <div class="card-value blue">{stats['total_commits_analyzed']}</div>
    <div class="card-label">Commits Analyzed</div>
  </div>
  <div class="card">
    <div class="card-value yellow">{stats['total_files_tracked']}</div>
    <div class="card-label">Files Changed</div>
  </div>
  <div class="card">
    <div class="card-value green">{stats['total_files_complex']}</div>
    <div class="card-label">Files Measured</div>
  </div>
</div>

<div class="charts">
  <div class="chart-card">
    <h2>Hotspot Scatter — Churn vs Complexity</h2>
    <canvas id="scatterChart"></canvas>
  </div>
  <div class="chart-card">
    <h2>Top 15 Files by Score</h2>
    <canvas id="barChart"></canvas>
  </div>
  <div class="chart-card full">
    <h2>Commit Activity</h2>
    <canvas id="heatChart"></canvas>
  </div>
  <div class="chart-card">
    <h2>Commits by Hour of Day</h2>
    <canvas id="hourChart"></canvas>
  </div>
  <div class="chart-card">
    <h2>Quadrant Guide</h2>
    <div class="quadrant-legend">
      <div class="q-item q-red"><strong class="red">CRITICAL ≥75</strong><br>High churn + high complexity.<br>Refactor immediately.</div>
      <div class="q-item q-yellow"><strong class="yellow">HIGH ≥50</strong><br>Actively changing, growing<br>complexity. Watch closely.</div>
      <div class="q-item q-blue"><strong class="blue">MEDIUM ≥25</strong><br>Low churn but complex.<br>Stable for now.</div>
      <div class="q-item q-green"><strong class="green">LOW &lt;25</strong><br>Simple and stable.<br>Healthy codebase.</div>
    </div>
    <p style="margin-top:16px; color: var(--dim); font-size: 0.8rem;">
      Bus Factor = number of authors who touched a file.<br>
      Bus Factor = 1 means only one person understands it — high risk.
    </p>
  </div>
</div>

<div class="section">
  <h2>Hotspot Files</h2>
  <table>
    <thead><tr>
      <th>#</th><th>File</th><th>Score</th><th>Churn</th>
      <th>Complexity</th><th>LOC</th><th>Bus Factor</th><th>Language</th>
    </tr></thead>
    <tbody>{hotspot_rows}</tbody>
  </table>
</div>

<div class="section">
  <h2>TODO Debt — {len(todos)} items (showing oldest 50)</h2>
  <table>
    <thead><tr>
      <th>Age</th><th>Kind</th><th>Location</th><th>Author</th><th>Text</th>
    </tr></thead>
    <tbody>{todo_rows}</tbody>
  </table>
</div>

<footer>
  Generated by <strong>git-hotspots</strong> ·
  Concept based on Adam Tornhill's "Your Code as a Crime Scene" ·
  Free &amp; open source
</footer>

<script>
const chartDefaults = {{
  color: '#e2e2f0',
  plugins: {{ legend: {{ labels: {{ color: '#6b7280' }} }} }},
}};
Chart.defaults.color = '#6b7280';

// Scatter chart
new Chart(document.getElementById('scatterChart'), {{
  type: 'bubble',
  data: {{
    datasets: [{{
      label: 'Files',
      data: {scatter_data},
      backgroundColor: function(ctx) {{
        const s = ctx.raw?.score || 0;
        if (s >= 75) return 'rgba(239,68,68,0.7)';
        if (s >= 50) return 'rgba(245,158,11,0.7)';
        if (s >= 25) return 'rgba(6,182,212,0.7)';
        return 'rgba(16,185,129,0.5)';
      }},
      borderColor: 'transparent',
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{
      tooltip: {{
        callbacks: {{
          label: (ctx) => `${{ctx.raw.full}} (score: ${{ctx.raw.score}})`,
        }}
      }},
      legend: {{ display: false }},
    }},
    scales: {{
      x: {{ title: {{ display: true, text: 'Churn (commits)', color: '#6b7280' }}, grid: {{ color: '#1e1e2a' }}, ticks: {{ color: '#6b7280' }} }},
      y: {{ title: {{ display: true, text: 'Complexity Score', color: '#6b7280' }}, grid: {{ color: '#1e1e2a' }}, ticks: {{ color: '#6b7280' }} }},
    }}
  }}
}});

// Bar chart
new Chart(document.getElementById('barChart'), {{
  type: 'bar',
  data: {{
    labels: {bar_labels},
    datasets: [{{
      label: 'Hotspot Score',
      data: {bar_scores},
      backgroundColor: {bar_colors},
      borderRadius: 4,
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ max: 100, grid: {{ color: '#1e1e2a' }}, ticks: {{ color: '#6b7280' }} }},
      y: {{ grid: {{ display: false }}, ticks: {{ color: '#6b7280', font: {{ size: 11 }} }} }},
    }}
  }}
}});

// Heatmap (line chart)
new Chart(document.getElementById('heatChart'), {{
  type: 'line',
  data: {{
    labels: {heat_labels},
    datasets: [{{
      label: 'Commits',
      data: {heat_values},
      borderColor: '#06b6d4',
      backgroundColor: 'rgba(6,182,212,0.1)',
      fill: true,
      tension: 0.3,
      pointRadius: 0,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ color: '#1e1e2a' }}, ticks: {{ color: '#6b7280', maxTicksLimit: 15 }} }},
      y: {{ grid: {{ color: '#1e1e2a' }}, ticks: {{ color: '#6b7280' }} }},
    }}
  }}
}});

// Hourly distribution
new Chart(document.getElementById('hourChart'), {{
  type: 'bar',
  data: {{
    labels: {hour_labels},
    datasets: [{{
      label: 'Commits',
      data: {hour_values},
      backgroundColor: 'rgba(139,92,246,0.7)',
      borderRadius: 3,
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ color: '#6b7280', maxRotation: 45 }} }},
      y: {{ grid: {{ color: '#1e1e2a' }}, ticks: {{ color: '#6b7280' }} }},
    }}
  }}
}});
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
