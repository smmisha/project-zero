export const LANDING_HTML = `<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>git-hotspots</title>
<style>
  :root{--bg:#0f0f13;--card:#1a1a24;--border:#2a2a3a;--text:#e2e2f0;--dim:#6b7280;--red:#ef4444;--yellow:#f59e0b;--green:#10b981;--blue:#06b6d4}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:'Inter',system-ui,sans-serif;min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px}
  .card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:40px 48px;max-width:620px;width:100%}
  h1{font-size:2rem;font-weight:800;color:var(--blue)}
  .tagline{color:var(--dim);margin:8px 0 32px;font-size:.95rem}
  label{display:block;font-size:.8rem;color:var(--dim);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
  input{width:100%;background:#111118;border:1px solid var(--border);border-radius:8px;color:var(--text);padding:10px 14px;font-size:.95rem;outline:none;transition:border-color .15s}
  input:focus{border-color:var(--blue)}
  .row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
  button{margin-top:24px;width:100%;padding:12px;background:var(--blue);color:#000;font-weight:700;font-size:1rem;border:none;border-radius:8px;cursor:pointer;transition:opacity .15s}
  button:hover{opacity:.85}button:disabled{opacity:.4;cursor:not-allowed}
  #status{margin-top:20px;font-size:.85rem;color:var(--dim);min-height:20px;text-align:center}
  #bar{margin-top:10px;height:3px;background:var(--border);border-radius:2px;overflow:hidden;display:none}
  #fill{height:100%;background:var(--blue);width:0;transition:width .3s}
  .pills{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}
  .pill{padding:4px 12px;border-radius:20px;font-size:.78rem;font-weight:500}
  .pill-red{background:rgba(239,68,68,.12);color:var(--red)}.pill-yellow{background:rgba(245,158,11,.12);color:var(--yellow)}
  .pill-blue{background:rgba(6,182,212,.12);color:var(--blue)}.pill-green{background:rgba(16,185,129,.12);color:var(--green)}
  footer{margin-top:24px;color:var(--dim);font-size:.78rem;text-align:center}
  a{color:var(--blue);text-decoration:none}
</style></head><body>
<div class="card">
  <h1>git-hotspots</h1>
  <p class="tagline">Find the riskiest files in any public GitHub repo — runs entirely on Cloudflare via the GitHub API.</p>
  <form id="form">
    <label for="url">GitHub repository URL</label>
    <input type="text" id="url" placeholder="https://github.com/pallets/flask" autocomplete="off" required>
    <div class="row">
      <div><label for="days" style="margin-top:16px">Days of history</label><input type="number" id="days" value="90" min="7" max="730"></div>
      <div><label for="top" style="margin-top:16px">Top N files</label><input type="number" id="top" value="20" min="5" max="50"></div>
    </div>
    <button type="submit" id="btn">Analyze →</button>
  </form>
  <div id="status"></div>
  <div id="bar"><div id="fill"></div></div>
  <div class="pills">
    <span class="pill pill-red">Hotspot score</span>
    <span class="pill pill-yellow">Bus factor</span>
    <span class="pill pill-blue">TODO debt</span>
    <span class="pill pill-green">No clone · pure API</span>
  </div>
</div>
<footer><a href="https://github.com/smmisha/project-zero" target="_blank">github.com/smmisha/project-zero</a> · Inspired by <em>Your Code as a Crime Scene</em></footer>
<script>
const f=document.getElementById('form'),btn=document.getElementById('btn'),st=document.getElementById('status'),bar=document.getElementById('bar'),fill=document.getElementById('fill');
f.addEventListener('submit',async e=>{
  e.preventDefault();
  btn.disabled=true;btn.textContent='Working…';bar.style.display='block';fill.style.width='15%';st.style.color='#6b7280';st.textContent='⟳  Querying GitHub API…';
  let tick=15;const iv=setInterval(()=>{tick=Math.min(90,tick+5);fill.style.width=tick+'%';},700);
  try{
    const resp=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      url:document.getElementById('url').value.trim(),
      days:+document.getElementById('days').value,
      top:+document.getElementById('top').value
    })});
    clearInterval(iv);
    if(!resp.ok){const j=await resp.json().catch(()=>({error:'Server error'}));st.style.color='#ef4444';st.textContent='✗  '+(j.error||('HTTP '+resp.status));btn.disabled=false;btn.textContent='Analyze →';fill.style.width='0';return;}
    fill.style.width='100%';st.textContent='✓  Done — rendering report…';
    const html=await resp.text();
    document.open();document.write(html);document.close();
  }catch(err){clearInterval(iv);st.style.color='#ef4444';st.textContent='✗  '+err.message;btn.disabled=false;btn.textContent='Analyze →';fill.style.width='0';}
});
</script>
</body></html>`;
