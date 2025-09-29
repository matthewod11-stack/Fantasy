#!/usr/bin/env bash
set -euo pipefail

echo "Starting Fantasy TikTok Engine API server..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check if uvicorn is available
if ! command -v uvicorn &> /dev/null; then
    echo "⚠️  uvicorn not found. Run 'make setup' first."
    exit 1
fi

# Start the API server
echo "🚀 Starting API server at http://127.0.0.1:8000"
echo "📖 API docs available at http://127.0.0.1:8000/docs"
echo "Press Ctrl+C to stop"

uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload