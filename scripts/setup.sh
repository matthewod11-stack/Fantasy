#!/usr/bin/env bash
set -euo pipefail

echo "Setting up Fantasy TikTok Engine development environment..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Make scripts executable
echo "Making scripts executable..."
chmod +x scripts/*.sh

echo "✅ Setup complete! Virtual environment is ready."
echo "To activate: source .venv/bin/activate"