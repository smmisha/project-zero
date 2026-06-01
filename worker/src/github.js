// GitHub REST API client — replaces `git clone` + `git log` + `git blame`.
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

// Limited-concurrency map to avoid hammering the API.
async function pool(items, concurrency, worker) {
  const results = [];
  let i = 0;
  async function run() {
    while (i < items.length) {
      const idx = i++;
      try {
        results[idx] = await worker(items[idx], idx);
      } catch {
        results[idx] = null;
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, run));
  return results;
}

export async function getDefaultBranch(owner, repo, token) {
  const data = await ghJson(`/repos/${owner}/${repo}`, token);
  return data.default_branch || "main";
}

// Returns { commits: [{sha, author, dateISO}], heatmap, hours }
export async function listCommits(owner, repo, sinceISO, token, maxPages = 8) {
  const commits = [];
  for (let page = 1; page <= maxPages; page++) {
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
  }
  return commits;
}

// Fetch per-commit file lists to build churn + per-file authors.
// Returns { churn: {path: count}, authors: {path: Set-as-array} }
export async function buildChurn(owner, repo, commits, token, maxDetail = 150) {
  const target = commits.slice(0, maxDetail);
  const churn = {};
  const authors = {};

  await pool(target, 6, async (c) => {
    const detail = await ghJson(`/repos/${owner}/${repo}/commits/${c.sha}`, token);
    const files = detail.files || [];
    for (const f of files) {
      const path = f.filename;
      if (!path) continue;
      churn[path] = (churn[path] || 0) + 1;
      if (!authors[path]) authors[path] = new Set();
      authors[path].add(c.author);
    }
  });

  const authorsArr = {};
  for (const [k, v] of Object.entries(authors)) authorsArr[k] = [...v];
  return { churn, authors: authorsArr, analyzed: target.length, total: commits.length };
}

// Fetch raw file contents for the given paths (most-churned first).
// Returns { path: contentString }. Uses the raw CDN (no API rate limit).
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
