# git-hotspots — Cloudflare Worker

A pure-JavaScript port of git-hotspots that runs entirely on Cloudflare
Workers. Instead of cloning a repo with `git`, it uses the **GitHub REST
API** to read commit history and the **raw CDN** to read file contents,
then computes hotspots in the Worker and returns an interactive HTML report.

## Why a separate implementation?

Cloudflare Workers can't run Python or spawn `git`. So the analysis was
re-implemented in JS against the GitHub API. The Python CLI (`main.py`) and
FastAPI app (`web_app.py`) in the repo root still work for local use; this
Worker is the deployable web version.

## Routes

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/`            | Landing page with the analysis form  |
| GET    | `/health`      | Health check (`{"status":"ok"}`)     |
| POST   | `/api/analyze` | `{url, days, top, exclude}` → HTML report |

## How it works

1. Resolve the repo's default branch (`GET /repos/:o/:r`).
2. List commits since N days (`GET /repos/:o/:r/commits`) → activity heatmap.
3. Fetch per-commit detail for the most recent ~150 commits → per-file churn
   and per-file authors (bus factor).
4. Fetch raw contents of the most-churned source files from
   `raw.githubusercontent.com` (this does **not** count against the API rate
   limit) → complexity score.
5. Score `log₂(churn+1) × complexity`, render HTML with Chart.js.

## Limits

Two limits apply, and the report tells you when either one cut the analysis
short. It never silently pretends to have seen all commits.

**GitHub API rate limit**

- **Unauthenticated: 60 requests/hour per IP** — enough for one or two analyses.
- **With a token: 5000 requests/hour** — recommended.

If the limit is hit before any commit could be read, you get a clear error.
If it is hit partway through, the report shows how many commits were
actually analyzed.

**Cloudflare subrequests**

A Worker on the free plan may make at most **50 outbound requests** per
invocation. `SUBREQUEST_BUDGET` (default `50`) makes the Worker plan within
that: after listing commits, ~60% of what is left goes to commit details
(churn, bus factor) and ~40% to file contents (complexity). On a paid
Workers plan raise it, e.g. to `1000`, for much fuller results.

Add a token as a secret:

```bash
cd worker
npx wrangler secret put GITHUB_TOKEN
```

When more commits exist than fit in the budget, the report analyzes the most
recent ones and shows a notice.

## Deploy

This repo is already wired to Cloudflare Workers Builds via `wrangler.toml`
at the repo root — pushing to the branch triggers a build. To deploy manually:

```bash
cd worker
npm install
npx wrangler deploy        # uses ../wrangler.toml
```

## Local development

```bash
cd worker
npm install
npx wrangler dev           # serves on http://localhost:8787
```

## Tuning (vars in `wrangler.toml`)

| Var                    | Default | Meaning                                   |
|------------------------|---------|-------------------------------------------|
| `MAX_COMMITS_DETAIL`   | 150     | Max commits fetched in detail for churn   |
| `MAX_FILES_COMPLEXITY` | 60      | Max source files fetched for complexity   |
| `SUBREQUEST_BUDGET`    | 50      | Outbound requests allowed per analysis    |

## Request body

```json
{ "url": "https://github.com/owner/repo", "days": 90, "top": 20, "exclude": "tests, docs" }
```

`exclude` is optional: a comma-separated list (or JSON array) of paths or
globs, same rules as the CLI's `--exclude`.

## Tests

```bash
cd worker
npm ci
npm test
```
