#!/usr/bin/env bash
set -euo pipefail

echo "Stopping Fantasy TikTok Engine services..."

# For local development, there's nothing to stop explicitly
# The uvicorn server is stopped with Ctrl+C
echo "ℹ️  Nothing to stop (local development mode)"
echo "Use Ctrl+C to stop the API server if running"