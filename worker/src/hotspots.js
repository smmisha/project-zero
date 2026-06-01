// Hotspot scoring + repo-level risk index — JS port of hotspots.py.

// score = log2(churn + 1) * complexity, normalized to 0-100 across the repo.
export function calculateHotspots(churn, complexity, authors, topN = 20) {
  const files = new Set([...Object.keys(churn), ...Object.keys(complexity)]);
  const hotspots = [];

  for (const file of files) {
    const churnCount = churn[file] || 0;
    const comp = complexity[file] || {};
    const compScore = comp.complexity_score || 0;
    if (churnCount === 0 && compScore === 0) continue;

    const rawScore = Math.log2(churnCount + 1) * compScore;
    const fileAuthors = [...new Set(authors[file] || [])];

    hotspots.push({
      file,
      churn: churnCount,
      complexity: compScore,
      loc: comp.loc || 0,
      functions: comp.function_count || 0,
      max_depth: comp.max_depth || 0,
      branches: comp.branch_count || 0,
      language: comp.language || "unknown",
      bus_factor: fileAuthors.length,
      authors: fileAuthors,
      raw_score: rawScore,
    });
  }

  if (hotspots.length === 0) return [];

  const maxScore = Math.max(...hotspots.map((h) => h.raw_score)) || 1;
  for (const h of hotspots) {
    h.score = Math.round((h.raw_score / maxScore) * 100 * 10) / 10;
  }

  hotspots.sort((a, b) => b.score - a.score);
  return hotspots.slice(0, topN);
}

export function getSummaryStats(hotspots, churn, complexity) {
  const totalCommits = Object.values(churn).reduce((a, b) => a + b, 0);
  const hotspotFiles = hotspots.filter((h) => h.score >= 75);
  return {
    total_files_tracked: Object.keys(churn).length,
    total_commits_analyzed: totalCommits,
    total_files_complex: Object.keys(complexity).length,
    hotspot_count: hotspotFiles.length,
    top_file: hotspots.length ? hotspots[0].file : null,
    top_score: hotspots.length ? hotspots[0].score : 0,
  };
}

// risk_index = sum(score^2 / 100) — concentrated severe risk ranks higher.
export function computeRiskIndex(hotspots) {
  if (!hotspots.length) {
    return { risk_index: 0, critical: 0, high: 0, medium: 0, silo_count: 0, silo_ratio: 0, top_file: null, top_score: 0 };
  }
  const critical = hotspots.filter((h) => h.score >= 75).length;
  const high = hotspots.filter((h) => h.score >= 50 && h.score < 75).length;
  const medium = hotspots.filter((h) => h.score >= 25 && h.score < 50).length;
  const silos = hotspots.filter((h) => h.bus_factor === 1);
  const riskIndex = hotspots.reduce((acc, h) => acc + (h.score * h.score) / 100, 0);
  return {
    risk_index: Math.round(riskIndex * 10) / 10,
    critical,
    high,
    medium,
    silo_count: silos.length,
    silo_ratio: Math.round((silos.length / hotspots.length) * 100) / 100,
    top_file: hotspots[0].file,
    top_score: hotspots[0].score,
  };
}
