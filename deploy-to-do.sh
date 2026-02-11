#!/bin/bash
# DigitalOcean Functions Setup and Deployment Script

set -e

echo "🚀 YouTube Stream URL - DigitalOcean Serverless Setup"
echo "=================================================="

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl CLI not found. Installing doctl..."
    cd ~
    wget https://github.com/digitalocean/doctl/releases/download/v1.115.0/doctl-1.115.0-linux-amd64.tar.gz
    tar xf ~/doctl-1.115.0-linux-amd64.tar.gz
    sudo mv ~/doctl /usr/local/bin
else
    echo "✅ doctl CLI found"
fi

# Authenticate with DigitalOcean
if [ -z "$DIGITALOCEAN_ACCESS_TOKEN" ]; then
    echo "❌ DIGITALOCEAN_ACCESS_TOKEN environment variable not set"
    echo "Please set your token: export DIGITALOCEAN_ACCESS_TOKEN='your_token_here'"
    exit 1
fi

echo "🔐 Authenticating with DigitalOcean..."
doctl auth init --access-token "$DIGITALOCEAN_ACCESS_TOKEN"

# Check connection
echo "🔍 Checking DigitalOcean connection..."
doctl account get

# List available namespaces
echo "📋 Available function namespaces:"
doctl serverless namespaces list || echo "No namespaces yet"

# Create or connect to namespace
NAMESPACE="default"
echo "📦 Using namespace: $NAMESPACE"

# Deploy the function
echo "📤 Deploying serverless function..."
doctl serverless deploy . --remote

# List deployed functions
echo "✅ Deployed functions:"
doctl serverless functions list

# Get function details
echo "📊 Function details:"
doctl serverless functions get default/stream-extractor

echo ""
echo "=================================================="
echo "✨ Deployment Complete!"
echo "Next steps:"
echo "1. Test the function endpoint"
echo "2. Configure GitHub Actions secrets with your token"
echo "3. Push to main branch to trigger automated deployment"
