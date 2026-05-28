# git-hotspots

**Codebase Risk Intelligence** — Find files that are both frequently changed *and* highly complex. Those are your bugs waiting to happen.

## Why this exists

Every codebase has files that everyone is afraid to touch. They're complex, they change constantly, and nobody fully understands them. `git-hotspots` surfaces exactly those files using two orthogonal signals:

- **Churn** — how often a file changes (from git history)
- **Complexity** — how hard it is to understand (branch count, nesting depth, function density)

The **Hotspot Score** = `log₂(churn + 1) × complexity` — files scoring high need refactoring attention first.

This is inspired by Adam Tornhill's research in *"Your Code as a Crime Scene"*, but unlike [CodeScene](https://codescene.com/) (commercial, cloud, expensive), this tool is **free, local, and runs in seconds**.

## Features

- **Hotspot detection** — ranked list of highest-risk files
- **Bus factor analysis** — spots knowledge silos (only 1 person understands a file)
- **TODO debt tracker** — ages every TODO/FIXME via `git blame`; oldest ones are most forgotten
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

# Last 30 days, top 20 files, save HTML report
python main.py --days 30 --top 20 --html report.html

# Skip TODO analysis (faster on large repos)
python main.py --no-todos

# JSON output for scripting
python main.py --json | jq '.hotspots[0:3]'
```

## Install

```bash
git clone https://github.com/yourname/git-hotspots
cd git-hotspots
pip install colorama       # optional, for colored terminal output
python main.py /your/repo
```

No other dependencies. Python 3.8+, any OS with git.

## Reading the output

```
#  RISK        Score  Churn  Cmplx  LOC  Bus  File
1  [CRITICAL]  100.0     10   57.4  892    1  src/core/app.py
```

| Column | Meaning |
|--------|---------|
| Score | Hotspot score 0–100 (higher = more risk) |
| Churn | Number of commits touching this file |
| Cmplx | Complexity score 0–100 (branch density × nesting) |
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
