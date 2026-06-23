#!/bin/bash
# Start script for Cloudflare Pages

cd /workspace/smmisha__project-zero/medexplainer

# Install dependencies
pip install -r requirements.txt

# Start the server
python server.py
