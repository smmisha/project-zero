# git-hotspots

**Codebase Risk Intelligence** — Find files that are both frequently changed *and* highly complex. Those are your bugs waiting to happen.

## Why this exists

Every codebase has files that everyone is afraid to touch. They're complex, they change constantly, and nobody fully understands them. `git-hotspots` surfaces exactly those files using two orthogonal signals:

- **Churn** — how often a file changes (from git history)
- **Complexity** — how hard it is to understand (branches, functions and nesting across the whole file, relative to the most complex file in the repo)

The **Hotspot Score** = `log₂(churn + 1) × complexity` — files scoring high need refactoring attention first.

This is inspired by Adam Tornhill's research in *"Your Code as a Crime Scene"*. Compared with [CodeScene](https://codescene.com/) (commercial, cloud) and Tornhill's own [code-maat](https://github.com/adamtornhill/code-maat) (free, needs a JVM and some scripting), this tool is **free, local, a single `python` command, and runs in seconds**.

## Features

- **Hotspot detection** — ranked list of highest-risk files
- **Bus factor analysis** — spots knowledge silos (only 1 person understands a file)
- **TODO debt tracker** — ages every TODO/FIXME/HACK/XXX/BUG via `git blame`; oldest ones are most forgotten
- **Commit heatmap** — visualizes activity over time in the terminal
- **Hourly patterns** — shows when your team commits (peak hours, late-night risk)
- **Interactive HTML report** — scatter plot, bar chart, activity timeline, fully self-contained
- **JSON output** — pipe results into other tools or scripts
- **No cloud, no tracking, no API keys**

## Usage

```bash
# Analyze current directory (last 90 days)
python main.py

# Analyze a specific repo
python main.py /path/to/repo

# Compare multiple repos side by side (portfolio mode)
python main.py service-a service-b service-c

# Last 30 days, top 20 files, save HTML report
python main.py --days 30 --top 20 --html report.html

# Ignore tests, docs and minified files (repeatable)
python main.py --exclude tests --exclude docs --exclude "*.min.js"

# Skip TODO analysis (faster on large repos)
python main.py --no-todos

# JSON output for scripting
python main.py --json | jq '.hotspots[0:3]'
```

## Portfolio mode (multiple repos)

Pass more than one repository path to compare them and find which codebase
carries the most risk:

```bash
python main.py ~/work/api ~/work/web ~/work/worker --days 180
```

```
Risk Ranking  (most → least risky)
 #  Repository   RiskIdx  Crit  High  Silos  Commits  Top Hotspot
 1  api             897.9     7     8     12      255  app/handlers.py (100)
 2  web             544.2     1    12      1      644  src/core.js (100)
```

| Column | Meaning |
|--------|---------|
| RiskIdx | Repo-level risk index — `Σ(score² / 100)` over hotspots. Concentrated, severe risk scores higher than many mild files. |
| Crit / High | Number of critical (≥75) and high (≥50) hotspot files |
| Silos | Files with bus factor 1 — only one author understands them |

Add `--compact` to show only the ranking table, or `--json` to get the full
comparison as structured data. `--html` applies to single-repo mode only.

## Install

Requires **Python 3.10+** and **git** on any OS.

```bash
git clone https://github.com/smmisha/project-zero
cd project-zero
pip install -r requirements.txt   # colorama (colors) + FastAPI (web app only)
python main.py /your/repo
```

The CLI itself needs nothing beyond the standard library; `colorama` just
adds colors.

### Windows

In PowerShell (install [Python](https://www.python.org/downloads/) with
"Add to PATH" checked, and [Git for Windows](https://git-scm.com/download/win)):

```powershell
git clone https://github.com/smmisha/project-zero
cd project-zero
py -m pip install -r requirements.txt
py main.py C:\path\to\your\repo --exclude tests --html report.html
start report.html
```

## Web app

A small FastAPI app lets you paste a public GitHub / GitLab / Bitbucket URL
and get the HTML report in the browser:

```bash
python web_app.py          # then open http://localhost:8000
```

It clones with `--depth 200` and refuses repositories larger than
`MAX_REPO_MB` (env var, default 500). `Dockerfile`, `render.yaml` and
`railway.json` are ready for deployment.

A JavaScript port that runs on **Cloudflare Workers** (GitHub API, no git
binary) lives in [`worker/`](worker/README.md).

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest            # Python tests

cd worker && npm ci && npm test   # Worker tests (Node 22+)
```

CI runs both on every push (`.github/workflows/ci.yml`).

## Reading the output

```
#  RISK        Score  Churn  Cmplx  LOC  Bus  File
1  [CRITICAL]  100.0     10   57.4  892    1  src/core/app.py
```

| Column | Meaning |
|--------|---------|
| Score | Hotspot score 0–100 (higher = more risk) |
| Churn | Number of commits touching this file |
| Cmplx | Complexity 0–100, relative to the most complex analyzed file (100 = that file) |
| LOC | Lines of code |
| Bus | Bus factor: number of unique authors. **1 = knowledge silo** |

### Risk quadrants

```
                    Low Complexity   High Complexity
High Churn          WATCH            ★ HOTSPOT ★
Low Churn           HEALTHY          LOW RISK
```

- **HOTSPOT** (red, score ≥ 75): Refactor this first. High change rate + high complexity = bugs.
- **WATCH** (yellow, score ≥ 50): Complexity growing while the file is active. Needs attention.
- **LOW RISK** (blue, score ≥ 25): Complex but stable. Document it.
- **HEALTHY** (green): Simple and rarely changes. Leave it alone.

## Supported languages

Python, JavaScript, TypeScript, JSX, TSX, Go, Rust, Java, Kotlin, Scala, C#, C, C++, Ruby, PHP, Swift, Dart

## Comparison

| Tool | Free | Local | Churn×Complexity | Bus Factor | TODO Debt | HTML Report |
|------|------|-------|-----------------|------------|-----------|-------------|
| **git-hotspots** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| CodeScene | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| SonarQube | partial | ❌ | ❌ | ❌ | ❌ | ✅ |
| `git log --stat` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Lizard | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |

## License

MIT
