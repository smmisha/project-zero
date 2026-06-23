// Cloudflare Pages Function for MedExplainer API
// Note: This is a placeholder. For full functionality, use a separate Python API service.

export async function onRequestGet(context) {
  const { request } = context;
  const url = new URL(request.url);
  const query = url.searchParams.get('query') || '';
  
  // This is a demo response - in production, call your Python API
  const demoResponse = {
    query: query,
    total_results: 0,
    summary: `Demo: Try deploying the Python API on Render/Railway for full functionality. Search query: "${query}"`,
    results: []
  };
  
  return new Response(JSON.stringify(demoResponse), {
    headers: { 'Content-Type': 'application/json' }
  });
}

export async function onRequestPost(context) {
  const { request } = context;
  const data = await request.json();
  const query = data.query || '';
  
  const demoResponse = {
    query: query,
    total_results: 0,
    summary: `Demo: Try deploying the Python API on Render/Railway for full functionality. Search query: "${query}"`,
    results: []
  };
  
  return new Response(JSON.stringify(demoResponse), {
    headers: { 'Content-Type': 'application/json' }
  });
}
