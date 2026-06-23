#!/usr/bin/env python3
"""
MedExplainer Server - Entry point for Cloudflare Pages and other deployments.
"""

import os
import sys
from pathlib import Path

# Add the medexplainer directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app
import uvicorn

if __name__ == "__main__":
    # Get port from environment variable (Cloudflare Pages uses PORT)
    port = int(os.environ.get("PORT", 8787))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting MedExplainer server on {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False  # Disable reload in production
    )
