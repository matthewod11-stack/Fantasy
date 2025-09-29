#!/usr/bin/env bash
set -euo pipefail

echo "Running Fantasy TikTok Engine tests..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "⚠️  pytest not found. Run 'make setup' first."
    exit 1
fi

# Run tests with quiet output
echo "🧪 Running test suite..."
pytest -q

echo "✅ Tests completed!"