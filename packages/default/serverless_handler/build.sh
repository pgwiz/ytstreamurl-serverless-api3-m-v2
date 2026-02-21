#!/bin/bash
set -e

# Build script for DigitalOcean Functions (Python 3.11)
echo "📦 Starting build process..."

# Install Node.js for yt-dlp JavaScript runtime support
echo "📦 Installing Node.js for JavaScript signature solving..."
apt-get update -qq && apt-get install -y -qq nodejs npm > /dev/null 2>&1 || (echo "⚠️  Node.js install failed (continuing anyway)" && true)
if command -v node &> /dev/null; then
    echo "✅ Node.js available: $(node --version)"
else
    echo "⚠️  Node.js not available"
fi

# Install Python requirements
PY="$(which python || which python3 || echo python)"
$PY -m pip install --upgrade pip

echo "🐍 Installing Python packages to vendor directory..."
rm -rf vendor
python -m pip install --upgrade pip
python -m pip install --no-cache-dir --target ./vendor -r requirements.txt

echo "🦕 Deno JS runtime will be installed at runtime if needed..."
echo "✅ Build complete"