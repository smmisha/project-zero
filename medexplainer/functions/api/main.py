"""
Cloudflare Worker entry point for MedExplainer API.
Note: This is a placeholder. For full Python support, use Cloudflare Pages with a separate API service.
"""

# Cloudflare Workers don't support full Python yet, so this is a placeholder
# For production, use:
# 1. Cloudflare Pages for static files (public/)
# 2. A separate service (Render, Railway, Fly.io) for the Python API

def on_request_get(context):
    """Handle GET requests for Cloudflare Workers."""
    request = context.request
    url = request.url
    
    # Simple proxy to API (for demo purposes)
    if url.path == "/api/search":
        return new Response(
            "MedExplainer API: For full functionality, deploy the Python backend on Render/Railway/Fly.io",
            status=200,
            headers={"Content-Type": "text/plain"}
        )
    
    # Serve static files
    return fetch(request)
