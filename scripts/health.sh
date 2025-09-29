#!/usr/bin/env bash
set -euo pipefail

echo "Checking Fantasy TikTok Engine API health..."

# Define the health endpoint
HEALTH_URL="http://127.0.0.1:8000/health"

# Check if the API is responding
if curl -s -f "$HEALTH_URL" > /dev/null; then
    echo "✅ API is healthy!"
    echo "📋 Health check response:"
    curl -s "$HEALTH_URL" | python3 -m json.tool 2>/dev/null || curl -s "$HEALTH_URL"
    echo ""
    echo "🔗 API Documentation: http://127.0.0.1:8000/docs"
else
    echo "❌ API is not responding at $HEALTH_URL"
    echo "💡 Try running: make up"
    exit 1
fi