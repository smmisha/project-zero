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
| POST   | `/api/analyze` | `{url, days, top}` → HTML report      |

## How it works

1. Resolve the repo's default branch (`GET /repos/:o/:r`).
2. List commits since N days (`GET /repos/:o/:r/commits`) → activity heatmap.
3. Fetch per-commit detail for the most recent ~150 commits → per-file churn
   and per-file authors (bus factor).
4. Fetch raw contents of the most-churned source files from
   `raw.githubusercontent.com` (this does **not** count against the API rate
   limit) → complexity score.
5. Score `log₂(churn+1) × complexity`, render HTML with Chart.js.

## Rate limits

- **Unauthenticated: 60 requests/hour** — enough for one or two small repos.
- **With a token: 5000 requests/hour** — recommended.

Add a token as a secret:

```bash
cd worker
npx wrangler secret put GITHUB_TOKEN
```

When more commits exist than the per-commit detail cap (`MAX_COMMITS_DETAIL`,
default 150), the report analyzes the most recent ones and shows a notice.

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
