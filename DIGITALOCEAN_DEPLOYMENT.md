# DigitalOcean Serverless Deployment Guide

## Overview

This guide explains how to deploy the YouTube Stream URL extraction service as a serverless function on DigitalOcean Functions with automated CI/CD pipeline using GitHub Actions.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Setup](#local-setup)
3. [DigitalOcean Configuration](#digitalocean-configuration)
4. [GitHub Actions Setup](#github-actions-setup)
5. [Deployment](#deployment)
6. [Testing & Monitoring](#testing--monitoring)
7. [Playground UI](#playground-ui)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- **doctl** - DigitalOcean Command Line Interface
- **Python 3.11** - Local development
- **Git** - Version control
- **GitHub Account** - For CI/CD
- **DigitalOcean Account** - For hosting

### Required Credentials
1. **DigitalOcean API Token** - For doctl authentication
2. **GitHub Account** - With push access to the repository

---

## Local Setup

### 1. Install DigitalOcean CLI (doctl)

**macOS:**
```bash
brew install doctl
```

**Linux:**
```bash
cd ~
wget https://github.com/digitalocean/doctl/releases/download/v1.98.4/doctl-1.98.4-linux-x86_64.tar.gz
tar xf ~/doctl-1.98.4-linux-x86_64.tar.gz
sudo mv ~/doctl /usr/local/bin
```

**Windows (PowerShell):**
```powershell
choco install doctl
# or download from: https://github.com/digitalocean/doctl/releases
```

### 2. Install Python Dependencies

```bash
# Navigate to project directory
cd ytstreamurl-serverless-api3-m-v2

# Create virtual environment (recommended)
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r serverless_requirements.txt
pip install pytest pytest-cov flake8  # For testing
```

### 3. Set Up DigitalOcean Authentication

```bash
# Get your API token from: https://cloud.digitalocean.com/account/api/tokens

export DIGITALOCEAN_ACCESS_TOKEN="your_token_here"

# Initialize doctl
doctl auth init --access-token "$DIGITALOCEAN_ACCESS_TOKEN"

# Verify authentication
doctl account get
```

---

## DigitalOcean Configuration

### 1. Create DigitalOcean App Namespace

```bash
# Create a new namespace (first time only)
doctl serverless namespaces create python-functions --region nyc3

# List namespaces
doctl serverless namespaces list
```

### 2. Project Structure

The DigitalOcean serverless project is configured in files:

- **`do-serverless.yml`** - Function configuration
- **`serverless_handler.py`** - Main handler code
- **`.github/workflows/deploy.yml`** - CI/CD workflow

### 3. Configuration Files Explained

#### do-serverless.yml
```yaml
name: youtube-stream-url-serverless
runtime: python3.11
main: serverless_handler.py:app
limits:
  timeout: 60000  # 60 seconds
  memory: 512     # 512 MB
web: true        # HTTP endpoint
```

#### serverless_handler.py
- `/api/stream/<video_id>` - Extract stream URL
- `/stream?url=...` - Relay stream through proxy
- `/health` - Health check
- `/logs` - View execution logs

---

## GitHub Actions Setup

### 1. Add Secrets to GitHub Repository

Go to: `Settings → Secrets and variables → Actions`

Add the following secrets:

#### DIGITALOCEAN_ACCESS_TOKEN
```
Your DigitalOcean API Token
```

Obtain from: https://cloud.digitalocean.com/account/api/tokens

#### Example
```
dop_v1_abcdef1234567890...
```

### 2. Verify Workflow File

The workflow file is located at: `.github/workflows/deploy.yml`

It has three main jobs:
1. **test** - Runs linting and unit tests
2. **build-and-deploy** - Deploys to DigitalOcean
3. **rollback** - Automatic rollback on failure

---

## Deployment

### Option 1: Manual Deployment (Local)

```bash
# 1. Authenticate
export DIGITALOCEAN_ACCESS_TOKEN="your_token"
doctl auth init --access-token "$DIGITALOCEAN_ACCESS_TOKEN"

# 2. Deploy
doctl serverless deploy . --remote

# 3. Verify
doctl serverless functions list
doctl serverless functions get default/stream-extractor

# 4. Get endpoint URL
doctl serverless functions get default/stream-extractor --format endpoint --no-header
```

### Option 2: Automated Deployment (GitHub Actions)

1. **Commit and Push**
```bash
git add .
git commit -m "Deploy YouTube stream URL serverless function"
git push origin main
```

2. **GitHub Actions Runs Automatically**
   - Go to: `Actions` tab in your GitHub repository
   - Monitor the workflow execution
   - Wait for successful completion

3. **Get Function URL**
   - After deployment, the function URL will be available in DigitalOcean
   - Format: `https://<namespace>-<region>.digitaloceanapp.com/api/stream/<video_id>`

### Option 3: Automated Script

```bash
# Make the deploy script executable
chmod +x deploy-to-do.sh

# Run the deployment
./deploy-to-do.sh
```

---

## Testing & Monitoring

### 1. Health Check

```bash
# Test if function is running
curl https://<your-function-url>/health

# Expected response
{
  "status": "healthy",
  "service": "youtube-stream-url"
}
```

### 2. Test Stream Extraction

```bash
# Extract YouTube stream URL
curl "https://<your-function-url>/api/stream/dQw4w9WgXcQ" \
  -H "Accept: application/json"

# Expected response
{
  "title": "Rick Astley - Never Gonna Give You Up",
  "url": "https://your-function.com/streamytlink?url=...",
  "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
  "duration": "212",
  "uploader": "Rick Astley",
  "id": "dQw4w9WgXcQ"
}
```

### 3. View Function Logs

#### Option A: Using doctl
```bash
doctl serverless activations list --limit 10
doctl serverless activations logs <activation-id>
```

#### Option B: Using DigitalOcean Console
- Go to DigitalOcean Dashboard
- Navigate to: Functions → Your Namespace
- View logs directly in the UI

### 4. Monitor Performance

```bash
# List recent invocations
doctl serverless activations list

# Get function stats
doctl serverless functions get default/stream-extractor

# View detailed activation
doctl serverless activations get <activation-id>
```

---

## Playground UI

### 1. Using the Serverless Playground

The project includes an enhanced Playground UI: `playground.html` + `playground-serverless.js`

### 2. Local Testing

```bash
# Start the Flask development server
python serverless_handler.py

# Open browser
# http://localhost:8000/playground
```

### 3. Using Serverless Endpoint

1. Open `playground.html` in your browser
2. Click "⚙️ Settings" (or use browser console)
3. Set the serverless endpoint URL:
   ```
   https://your-function-url
   ```
4. Enter a YouTube video ID
5. Click "Extract Stream"

### 4. Features

- 🎬 Video ID extraction from YouTube URLs
- 📊 Real-time logging
- 🎵 Audio player integration
- 📋 API response inspection
- 🔗 Copy stream URLs
- ✅ Health check

---

## Environment Variables

Configure in `do-serverless.yml`:

```yaml
environment:
  YT_DLP_PATH: /usr/local/bin/yt-dlp
  LOG_DIR: /tmp/proxyLogs
  REQUEST_TIMEOUT: "45"
  COOKIES_FILE: /tmp/cookies.txt
  PYTHONUNBUFFERED: "1"
```

For sensitive data, use DigitalOcean Secrets:

```bash
doctl serverless function create \
  --env-from-secret SPOTIFY_TOKEN=your-secret \
  ...
```

---

## API Reference

### Extract Stream URL

**Endpoint:** `GET /api/stream/{video_id}`

**Parameters:**
- `video_id` (path) - YouTube video ID

**Response:**
```json
{
  "title": "string",
  "url": "string",
  "thumbnail": "string",
  "duration": "number",
  "uploader": "string",
  "id": "string",
  "ext": "string"
}
```

**Example:**
```bash
curl "https://your-function/api/stream/dQw4w9WgXcQ"
```

### Stream Relay

**Endpoint:** `GET /streamytlink?url=...`

**Parameters:**
- `url` (query) - Target stream URL to relay

**Response:** Video stream (mp4 or other format)

### Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "youtube-stream-url"
}
```

### View Logs

**Endpoint:** `GET /logs`

**Response:**
```json
{
  "logs": [
    {
      "video_id": "dQw4w9WgXcQ",
      "timestamp": "2024-02-11 10:30:45",
      "success": true,
      "stdout": "...",
      "stderr": ""
    }
  ]
}
```

---

## Troubleshooting

### Issue: "yt-dlp not found"

**Solution:**
```bash
# Install yt-dlp in DigitalOcean function environment
# Add to requirements.txt
pip install yt-dlp==2024.1.16
```

### Issue: "Function timeout"

**Solution:**
```yaml
# Increase timeout in do-serverless.yml
limits:
  timeout: 120000  # 120 seconds
```

### Issue: "No authentication token"

**Solution:**
```bash
# Set environment variable
export DIGITALOCEAN_ACCESS_TOKEN="dop_v1_..."
doctl auth init --access-token "$DIGITALOCEAN_ACCESS_TOKEN"
```

### Issue: "CORS errors in browser"

**Solution:**
The serverless function includes CORS headers. If still getting errors:
1. Check browser console for exact error
2. Verify endpoint URL is correct
3. Check function logs for server-side errors

### Issue: "GitHub Actions workflow fails"

**Solution:**
1. Check GitHub Actions logs: `Actions` tab
2. Verify `DIGITALOCEAN_ACCESS_TOKEN` secret is set correctly
3. Ensure DigitalOcean account is active and has available resources
4. Check doctl version compatibility

### Check Function Status

```bash
# List all functions
doctl serverless functions list

# Get specific function details
doctl serverless functions get default/stream-extractor

# Test function directly
doctl serverless functions invoke default/stream-extractor --data '{"video_id": "dQw4w9WgXcQ"}'
```

---

## File Structure

```
ytstreamurl-serverless-api3-m-v2/
├── serverless_handler.py           # Main Flask app
├── do-serverless.yml               # DigitalOcean config
├── serverless_requirements.txt      # Python dependencies
├── deploy-to-do.sh                 # Deployment script
├── playground.html                 # UI
├── playground-serverless.js        # Updated UI logic
├── .github/
│   └── workflows/
│       └── deploy.yml              # GitHub Actions CI/CD
├── tests/
│   └── test_serverless_handler.py  # Tests
└── README.md
```

---

## Next Steps

1. ✅ Set up local environment
2. ✅ Configure GitHub secrets
3. ✅ Test locally: `python serverless_handler.py`
4. ✅ Deploy to DigitalOcean
5. ✅ Test serverless endpoint
6. ✅ Set up monitoring and alerts
7. ✅ Use Playground UI for testing

---

## Support & Resources

- **DigitalOcean Docs:** https://docs.digitalocean.com/products/functions/
- **doctl Reference:** https://docs.digitalocean.com/reference/doctl/
- **GitHub Actions:** https://docs.github.com/actions
- **YouTube DLP:** https://github.com/yt-dlp/yt-dlp

---

## License

This project is provided as-is. Ensure you have permission to extract and serve YouTube content as per their Terms of Service.
