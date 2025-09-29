#!/usr/bin/env bash
set -euo pipefail

echo "Formatting Fantasy TikTok Engine code..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check if ruff is available, install if missing
if ! command -v ruff &> /dev/null; then
    echo "⚠️  ruff not found. Installing..."
    pip install ruff
fi

# Format code
echo "🎨 Formatting code with ruff..."
ruff format .

echo "✅ Code formatting complete!"