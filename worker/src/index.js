// git-hotspots — Cloudflare Worker entry point.
// Routes:
//   GET  /            → landing page
//   GET  /health      → {status:"ok"}
//   POST /api/analyze → analyze a GitHub repo, return an HTML report

import { LANDING_HTML } from "./landing.js";
import {
  parseRepoUrl,
  getDefaultBranch,
  listCommits,
  buildChurn,
  fetchFileContents,
  buildHeatmaps,
  GitHubError,
} from "./github.js";
import { analyzeContent, isSourceFile } from "./complexity.js";
import { calculateHotspots, getSummaryStats, computeRiskIndex } from "./hotspots.js";
import { findTodos } from "./todos.js";
import { generateReportHtml } from "./report.js";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function html(body, status = 200) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

async function handleAnalyze(request, env) {
  let payload;
  try {
    payload = await request.json();
  } catch {
    return json({ error: "Invalid JSON body." }, 400);
  }

  const parsed = parseRepoUrl(payload.url);
  if (!parsed) {
    return json({ error: "Provide a valid public GitHub URL, e.g. https://github.com/owner/repo." }, 400);
  }
  const { owner, repo } = parsed;
  const days = Math.max(7, Math.min(Number(payload.days) || 90, 730));
  const top = Math.max(5, Math.min(Number(payload.top) || 20, 50));

  const token = env.GITHUB_TOKEN || null;
  const maxDetail = Number(env.MAX_COMMITS_DETAIL) || 150;
  const maxFiles = Number(env.MAX_FILES_COMPLEXITY) || 60;

  const sinceISO = new Date(Date.now() - days * 86400000).toISOString();

  try {
    const branch = await getDefaultBranch(owner, repo, token);
    const commits = await listCommits(owner, repo, sinceISO, token);
    if (commits.length === 0) {
      return json({ error: `No commits found in the last ${days} days.` }, 404);
    }

    const { churn, authors, analyzed, total } = await buildChurn(owner, repo, commits, token, maxDetail);

    // Pick the most-churned source files for complexity analysis.
    const sourcePaths = Object.keys(churn)
      .filter(isSourceFile)
      .sort((a, b) => churn[b] - churn[a]);

    const contents = await fetchFileContents(owner, repo, branch, sourcePaths, maxFiles);

    const complexity = {};
    for (const [path, text] of Object.entries(contents)) {
      const m = analyzeContent(path, text);
      if (m) complexity[path] = m;
    }

    const hotspots = calculateHotspots(churn, complexity, authors, top);
    const stats = getSummaryStats(hotspots, churn, complexity);
    const risk = computeRiskIndex(hotspots);

    // TODO scan over the content of the top hotspots we already fetched.
    const topPaths = hotspots.slice(0, 10).map((h) => h.file);
    const topContents = {};
    for (const p of topPaths) if (contents[p]) topContents[p] = contents[p];
    const todos = findTodos(topContents);

    const { heatmap, hours } = buildHeatmaps(commits);

    const report = generateReportHtml({
      hotspots,
      todos,
      stats,
      risk,
      heatmap,
      hours,
      repoName: `${owner}/${repo}`,
      days,
      partial: analyzed < total ? { analyzed, total } : null,
    });

    return html(report);
  } catch (err) {
    if (err instanceof GitHubError) {
      return json({ error: err.message }, err.status >= 400 && err.status < 600 ? err.status : 502);
    }
    return json({ error: `Analysis failed: ${err.message}` }, 500);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return html(LANDING_HTML);
    }
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ status: "ok" });
    }
    if (request.method === "POST" && url.pathname === "/api/analyze") {
      return handleAnalyze(request, env);
    }
    return new Response("Not found", { status: 404 });
  },
};
