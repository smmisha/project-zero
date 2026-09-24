// GitHub REST API client — replaces `git clone` + `git log` + `git blame`.
//
// Every outbound fetch is charged to a SubrequestBudget: Cloudflare caps
// subrequests per invocation (50 on the free plan) and fetches past the cap
// fail. Running out of budget or hitting GitHub's rate limit is reported back
// to the caller, never swallowed, so the report can say it is partial.
//
// Strategy:
//   1. Resolve default branch.
//   2. List commits since N days (cheap: 100/page) → heatmap, hours, dates.
//   3. Fetch per-commit detail for the most recent MAX_COMMITS_DETAIL commits
//      → per-file churn + per-file authors (the expensive part).
//   4. Fetch raw file contents for the most-churned source files
//      (raw.githubusercontent.com — does NOT count against the API rate limit).

const API = "https://api.github.com";

export function parseRepoUrl(url) {
  const m = (url || "").trim().match(
    /^https:\/\/github\.com\/([\w.\-]+)\/([\w.\-]+?)(?:\.git)?\/?$/
  );
  if (!m) return null;
  return { owner: m[1], repo: m[2] };
}

function ghHeaders(token) {
  const h = {
    Accept: "application/vnd.github+json",
    "User-Agent": "git-hotspots-worker",
    "X-GitHub-Api-Version": "2022-11-28",
  };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

async function ghJson(path, token) {
  const resp = await fetch(`${API}${path}`, { headers: ghHeaders(token) });
  if (resp.status === 403 || resp.status === 429) {
    const remaining = resp.headers.get("x-ratelimit-remaining");
    if (remaining === "0") {
      throw new GitHubError(
        "GitHub API rate limit reached. Add a GITHUB_TOKEN secret to raise it to 5000/hr.",
        429
      );
    }
    throw new GitHubError("GitHub API access forbidden (private repo or rate limited).", 403);
  }
  if (resp.status === 404) {
    throw new GitHubError("Repository not found (check the URL or that it is public).", 404);
  }
  if (!resp.ok) {
    throw new GitHubError(`GitHub API error ${resp.status}.`, resp.status);
  }
  return resp.json();
}

export class GitHubError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export class SubrequestBudget {
  constructor(limit) {
    this.left = limit;
  }
  take() {
    if (this.left <= 0) return false;
    this.left--;
    return true;
  }
}

// Limited-concurrency map to avoid hammering the API. Returns
// { results, errors, stopped }: a worker that throws is recorded in errors;
// if shouldStop(err) is true for that error, no further items are started.
async function pool(items, concurrency, worker, shouldStop = () => false) {
  const results = [];
  const errors = [];
  let i = 0;
  let stopped = false;
  async function run() {
    while (!stopped && i < items.length) {
      const idx = i++;
      try {
        results[idx] = await worker(items[idx], idx);
      } catch (err) {
        results[idx] = null;
        errors.push(err);
        if (shouldStop(err)) stopped = true;
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, run));
  return { results, errors, stopped };
}

const isRateLimit = (err) => err instanceof GitHubError && (err.status === 429 || err.status === 403);

export async function getDefaultBranch(owner, repo, token, budget) {
  if (budget && !budget.take()) throw new GitHubError("Subrequest budget exhausted.", 503);
  const data = await ghJson(`/repos/${owner}/${repo}`, token);
  return data.default_branch || "main";
}

// Returns { commits: [{sha, author, dateISO}], heatmap, hours }
// Pages beyond the budget are not fetched; `truncated` reports that.
export async function listCommits(owner, repo, sinceISO, token, maxPages = 8, budget = null) {
  const commits = [];
  let truncated = false;
  for (let page = 1; page <= maxPages; page++) {
    if (budget && !budget.take()) {
      truncated = page > 1;
      if (page === 1) throw new GitHubError("Subrequest budget exhausted.", 503);
      break;
    }
    const batch = await ghJson(
      `/repos/${owner}/${repo}/commits?since=${sinceISO}&per_page=100&page=${page}`,
      token
    );
    if (!Array.isArray(batch) || batch.length === 0) break;
    for (const c of batch) {
      const author =
        (c.author && c.author.login) ||
        (c.commit && c.commit.author && c.commit.author.name) ||
        "unknown";
      const dateISO = c.commit && c.commit.author && c.commit.author.date;
      commits.push({ sha: c.sha, author, dateISO });
    }
    if (batch.length < 100) break;
    if (page === maxPages) truncated = true;
  }
  return { commits, truncated };
}

// Fetch per-commit file lists to build churn + per-file authors.
// Returns { churn, authors, analyzed, total, rateLimited }.
// `analyzed` counts only commits whose detail was actually fetched.
// Throws if not a single commit could be fetched.
export async function buildChurn(owner, repo, commits, token, maxDetail = 150) {
  const target = commits.slice(0, maxDetail);
  const fileLists = new Array(target.length).fill(null);

  const { errors } = await pool(target, 6, async (c, idx) => {
    const detail = await ghJson(`/repos/${owner}/${repo}/commits/${c.sha}`, token);
    fileLists[idx] = detail.files || [];
  }, isRateLimit);

  const analyzed = fileLists.filter((f) => f !== null).length;
  if (analyzed === 0 && errors.length > 0) throw errors[0];

  const { churn, authors } = tallyChurn(target, fileLists);
  return {
    churn,
    authors,
    analyzed,
    total: commits.length,
    rateLimited: errors.some(isRateLimit),
  };
}

// Turn per-commit file lists into churn + authors, following renames — same
// rules as git_analyzer._changes_per_commit. Commits must be newest first
// (the GitHub API order); fetches finish out of order, so this runs after
// the pool, never inside it. A null entry is a commit that wasn't fetched.
export function tallyChurn(commits, fileLists) {
  const renamedTo = {};
  const resolve = (path) => {
    const seen = new Set();
    while (Object.hasOwn(renamedTo, path) && !seen.has(path)) {
      seen.add(path);
      path = renamedTo[path];
    }
    return path;
  };

  const churn = {};
  const authors = {};
  commits.forEach((c, idx) => {
    const files = fileLists[idx];
    if (!files) return;
    const touched = new Set();
    for (const f of files) {
      if (!f.filename || f.status === "unchanged") continue;
      const current = resolve(f.filename);
      if (f.status === "renamed" && f.previous_filename) {
        renamedTo[f.previous_filename] = current;
      }
      touched.add(current);
    }
    for (const path of touched) {
      churn[path] = (churn[path] || 0) + 1;
      if (!authors[path]) authors[path] = new Set();
      authors[path].add(c.author);
    }
  });

  const authorsArr = {};
  for (const [k, v] of Object.entries(authors)) authorsArr[k] = [...v];
  return { churn, authors: authorsArr };
}

// Fetch raw file contents for the given paths (most-churned first).
// Returns { path: contentString }. Uses the raw CDN (no API rate limit).
// A missing file (deleted since it was changed) is simply skipped.
export async function fetchFileContents(owner, repo, branch, paths, maxFiles = 60) {
  const targets = paths.slice(0, maxFiles);
  const contents = {};

  await pool(targets, 8, async (path) => {
    const url = `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${encodeURI(path)}`;
    const resp = await fetch(url, { headers: { "User-Agent": "git-hotspots-worker" } });
    if (resp.ok) {
      const len = resp.headers.get("content-length");
      if (len && Number(len) > 500000) return;
      contents[path] = await resp.text();
    }
  });

  return contents;
}

export function buildHeatmaps(commits) {
  const heatmap = {};
  const hours = {};
  for (const c of commits) {
    if (!c.dateISO) continue;
    const d = new Date(c.dateISO);
    const day = d.toISOString().slice(0, 10);
    heatmap[day] = (heatmap[day] || 0) + 1;
    const hr = d.getUTCHours();
    hours[hr] = (hours[hr] || 0) + 1;
  }
  return { heatmap, hours };
}
