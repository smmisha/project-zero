// Cloudflare Pages Function for MedExplainer API
// This is a demo API - for full functionality, deploy Python backend separately

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  
  // Handle GET requests
  if (request.method === 'GET') {
    const query = url.searchParams.get('query') || '';
    
    const demoResponse = {
      query: query,
      total_results: 0,
      summary: `MedExplainer Demo: For full functionality, deploy the Python API on Render/Railway. Try searching for "vitamin D depression".`,
      results: []
    };
    
    return new Response(JSON.stringify(demoResponse), {
      headers: { 
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });
  }
  
  // Handle POST requests
  if (request.method === 'POST') {
    try {
      const data = await request.json();
      const query = data.query || '';
      
      const demoResponse = {
        query: query,
        total_results: 0,
        summary: `MedExplainer Demo: For full functionality, deploy the Python API on Render/Railway. Try searching for "vitamin D depression".`,
        results: []
      };
      
      return new Response(JSON.stringify(demoResponse), {
        headers: { 
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      });
    } catch (error) {
      return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
  
  // Handle OPTIONS for CORS
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
      }
    });
  }
  
  return new Response('Method not allowed', { status: 405 });
}
