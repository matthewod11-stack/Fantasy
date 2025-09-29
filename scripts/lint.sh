#!/usr/bin/env bash
set -euo pipefail

echo "Linting Fantasy TikTok Engine code..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check if ruff is available, install if missing
if ! command -v ruff &> /dev/null; then
    echo "⚠️  ruff not found. Installing..."
    pip install ruff
fi

# Lint code
echo "🔍 Linting code with ruff..."
ruff check .

echo "✅ Code linting complete!"