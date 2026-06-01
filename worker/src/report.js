// Generate a self-contained interactive HTML report — JS port of
// reporter.generate_html_report (Chart.js scatter/bar/timeline + tables).

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function basename(p) {
  const parts = String(p).split("/");
  return parts[parts.length - 1];
}

export function generateReportHtml({ hotspots, todos, stats, risk, heatmap, hours, repoName, days, partial }) {
  const top = hotspots.slice(0, 30);

  const scatterData = JSON.stringify(
    top.map((h) => ({
      x: h.churn,
      y: Math.round(h.complexity * 10) / 10,
      r: Math.max(5, Math.min(20, Math.floor(h.loc / 50))),
      full: h.file,
      score: h.score,
    }))
  );

  const bar = top.slice(0, 15);
  const barLabels = JSON.stringify(bar.map((h) => basename(h.file)));
  const barScores = JSON.stringify(bar.map((h) => h.score));
  const barColors = JSON.stringify(
    bar.map((h) => (h.score >= 75 ? "#ef4444" : h.score >= 50 ? "#f59e0b" : "#06b6d4"))
  );

  const heatKeys = Object.keys(heatmap).sort();
  const heatLabels = JSON.stringify(heatKeys);
  const heatValues = JSON.stringify(heatKeys.map((k) => heatmap[k]));

  const hourLabels = JSON.stringify(Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`));
  const hourValues = JSON.stringify(Array.from({ length: 24 }, (_, h) => hours[h] || 0));

  const hotspotRows = hotspots
    .slice(0, 30)
    .map((h, i) => {
      const scoreClass = h.score >= 75 ? "score-red" : h.score >= 50 ? "score-yellow" : "score-blue";
      const busClass = h.bus_factor === 1 ? "text-red" : h.bus_factor <= 2 ? "text-yellow" : "text-green";
      return `<tr>
        <td class="text-dim">${i + 1}</td>
        <td class="mono">${esc(h.file)}</td>
        <td class="${scoreClass}">${h.score}</td>
        <td>${h.churn}</td>
        <td>${h.complexity.toFixed(1)}</td>
        <td>${h.loc}</td>
        <td class="${busClass}">${h.bus_factor}</td>
        <td class="text-dim">${esc(h.language)}</td>
      </tr>`;
    })
    .join("");

  const todoRows = todos
    .slice(0, 60)
    .map((t) => {
      const kindClass = ["FIXME", "BUG", "HACK"].includes(t.kind) ? "badge-red" : "badge-yellow";
      return `<tr>
        <td><span class="badge ${kindClass}">${esc(t.kind)}</span></td>
        <td class="mono">${esc(t.file)}:${t.line}</td>
        <td class="text-dim">${esc(t.text.slice(0, 90))}</td>
      </tr>`;
    })
    .join("");

  const partialNote = partial
    ? `<div class="note">Analyzed the ${partial.analyzed} most recent of ${partial.total} commits (capped for API limits). Add a GITHUB_TOKEN secret for full history.</div>`
    : "";

  return `<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>git-hotspots — ${esc(repoName)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root{--bg:#0f0f13;--card:#1a1a24;--border:#2a2a3a;--text:#e2e2f0;--dim:#6b7280;--red:#ef4444;--yellow:#f59e0b;--green:#10b981;--blue:#06b6d4;--purple:#8b5cf6}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;padding:24px}
  h1{font-size:1.8rem;font-weight:700;color:var(--blue)}
  h2{font-size:1.1rem;font-weight:600;margin-bottom:16px}
  .subtitle{color:var(--dim);font-size:.9rem;margin-top:4px}
  .header{margin-bottom:24px}
  .note{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);color:var(--yellow);padding:10px 14px;border-radius:8px;font-size:.85rem;margin-bottom:24px}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:32px}
  .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px}
  .card-value{font-size:2rem;font-weight:700}
  .card-label{color:var(--dim);font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;margin-top:4px}
  .red{color:var(--red)}.yellow{color:var(--yellow)}.green{color:var(--green)}.blue{color:var(--blue)}
  .charts{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:32px}
  .chart-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px}
  .chart-card.full{grid-column:1/-1}
  canvas{max-height:320px}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  th{color:var(--dim);font-weight:500;text-align:left;padding:8px 12px;border-bottom:1px solid var(--border);font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}
  td{padding:8px 12px;border-bottom:1px solid #1e1e2a}
  tr:hover td{background:#1e1e2a}
  .mono{font-family:'Fira Code',monospace;font-size:.8rem;color:var(--blue)}
  .text-dim{color:var(--dim)}.text-red{color:var(--red);font-weight:600}.text-yellow{color:var(--yellow)}.text-green{color:var(--green)}
  .score-red{color:var(--red);font-weight:700}.score-yellow{color:var(--yellow);font-weight:600}.score-blue{color:var(--blue)}
  .badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.75rem;font-weight:600}
  .badge-red{background:rgba(239,68,68,.15);color:var(--red)}.badge-yellow{background:rgba(245,158,11,.15);color:var(--yellow)}
  .section{margin-bottom:32px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;overflow-x:auto}
  footer{text-align:center;color:var(--dim);font-size:.8rem;margin-top:32px;padding-top:16px;border-top:1px solid var(--border)}
  a{color:var(--blue);text-decoration:none}
</style></head><body>
<div class="header">
  <h1>git-hotspots</h1>
  <div class="subtitle">${esc(repoName)} · last ${days} days · analyzed via GitHub API on Cloudflare</div>
</div>
${partialNote}
<div class="cards">
  <div class="card"><div class="card-value red">${risk.critical}</div><div class="card-label">Critical Hotspots</div></div>
  <div class="card"><div class="card-value blue">${stats.total_commits_analyzed}</div><div class="card-label">Commits Analyzed</div></div>
  <div class="card"><div class="card-value yellow">${stats.total_files_tracked}</div><div class="card-label">Files Changed</div></div>
  <div class="card"><div class="card-value green">${risk.silo_count}</div><div class="card-label">Knowledge Silos</div></div>
</div>
<div class="charts">
  <div class="chart-card"><h2>Churn vs Complexity</h2><canvas id="scatter"></canvas></div>
  <div class="chart-card"><h2>Top 15 by Score</h2><canvas id="bar"></canvas></div>
  <div class="chart-card full"><h2>Commit Activity</h2><canvas id="heat"></canvas></div>
  <div class="chart-card"><h2>Commits by Hour (UTC)</h2><canvas id="hour"></canvas></div>
  <div class="chart-card">
    <h2>How to read this</h2>
    <p style="color:var(--dim);font-size:.85rem;line-height:1.6">
      <strong class="red">Score ≥ 75</strong>: high churn + high complexity → refactor first.<br>
      <strong class="yellow">≥ 50</strong>: actively changing, watch it.<br>
      <strong class="blue">≥ 25</strong>: complex but stable.<br><br>
      <strong>Bus factor = 1</strong> means only one author touched the file — a knowledge silo.
    </p>
  </div>
</div>
<div class="section">
  <h2>Hotspot Files</h2>
  <table><thead><tr><th>#</th><th>File</th><th>Score</th><th>Churn</th><th>Complexity</th><th>LOC</th><th>Bus Factor</th><th>Language</th></tr></thead>
  <tbody>${hotspotRows}</tbody></table>
</div>
<div class="section">
  <h2>TODO Debt — ${todos.length} items</h2>
  <table><thead><tr><th>Kind</th><th>Location</th><th>Text</th></tr></thead>
  <tbody>${todoRows || '<tr><td colspan="3" class="text-dim">None found in analyzed files.</td></tr>'}</tbody></table>
</div>
<footer>
  Generated by <a href="https://github.com/smmisha/project-zero" target="_blank">git-hotspots</a> on Cloudflare Workers ·
  Concept from Adam Tornhill's "Your Code as a Crime Scene"
</footer>
<script>
Chart.defaults.color='#6b7280';
new Chart(document.getElementById('scatter'),{type:'bubble',data:{datasets:[{data:${scatterData},backgroundColor:c=>{const s=c.raw?.score||0;return s>=75?'rgba(239,68,68,.7)':s>=50?'rgba(245,158,11,.7)':s>=25?'rgba(6,182,212,.7)':'rgba(16,185,129,.5)'},borderColor:'transparent'}]},options:{plugins:{tooltip:{callbacks:{label:c=>c.raw.full+' (score: '+c.raw.score+')'}},legend:{display:false}},scales:{x:{title:{display:true,text:'Churn (commits)'},grid:{color:'#1e1e2a'}},y:{title:{display:true,text:'Complexity'},grid:{color:'#1e1e2a'}}}}});
new Chart(document.getElementById('bar'),{type:'bar',data:{labels:${barLabels},datasets:[{data:${barScores},backgroundColor:${barColors},borderRadius:4}]},options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{max:100,grid:{color:'#1e1e2a'}},y:{grid:{display:false},ticks:{font:{size:11}}}}}});
new Chart(document.getElementById('heat'),{type:'line',data:{labels:${heatLabels},datasets:[{data:${heatValues},borderColor:'#06b6d4',backgroundColor:'rgba(6,182,212,.1)',fill:true,tension:.3,pointRadius:0}]},options:{plugins:{legend:{display:false}},scales:{x:{grid:{color:'#1e1e2a'},ticks:{maxTicksLimit:15}},y:{grid:{color:'#1e1e2a'}}}}});
new Chart(document.getElementById('hour'),{type:'bar',data:{labels:${hourLabels},datasets:[{data:${hourValues},backgroundColor:'rgba(139,92,246,.7)',borderRadius:3}]},options:{plugins:{legend:{display:false}},scales:{x:{grid:{display:false}},y:{grid:{color:'#1e1e2a'}}}}});
</script>
</body></html>`;
}
