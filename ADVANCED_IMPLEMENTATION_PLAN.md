# Advanced Plan: YouTube Streaming Serverless Function on DigitalOcean with CI/CD

## Executive Summary

This is a comprehensive plan to deploy a YouTube stream URL extraction service as a serverless function on DigitalOcean with automated CI/CD pipeline using GitHub Actions. The solution includes automated testing, deployment, rollback capabilities, and a modern Playground UI for interactive testing.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repository                         │
│  - Code changes trigger GitHub Actions workflow              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              GitHub Actions CI/CD Pipeline                   │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Test Job    │→ │ Deploy Job   │→ │ Rollback (if fail) │  │
│  │ - Lint      │  │ - Build      │  │ - Revert           │  │
│  │ - Test      │  │ - Deploy     │  │ - Notify           │  │
│  │ - Validate  │  │ - Smoke Test │  └────────────────────┘  │
│  └─────────────┘  └──────────────┘                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│           DigitalOcean Serverless Functions                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Python 3.11 Function Container                      │   │
│  │  • stream-extractor (POST /api/stream/<video_id>)   │   │
│  │  • stream-relay (GET /streamytlink?url=...)          │   │
│  │  • health-check (GET /health)                        │   │
│  │  • logs-viewer (GET /logs)                           │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Dependencies: yt-dlp, Flask, Requests               │   │
│  │  Environment: Python 3.11, 512 MB RAM                │   │
│  │  Timeout: 60 seconds per request                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ↓                    ↓                    ↓
    ┌─────────┐          ┌──────────┐      ┌─────────────┐
    │ Internet│          │  Logging │      │  Monitoring │
    │ (HTTP)  │          │ (Stdout) │      │  (built-in) │
    └─────────┘          └──────────┘      └─────────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────────┐
│              Playground UI (Browser)                         │
│  - Real-time logging console                                │
│  - Video ID/URL input                                       │
│  - Stream extraction                                        │
│  - Audio player integration                                 │
│  - API response inspection                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Hours 1-2)

**Objective:** Set up the serverless function handler and dependencies

**Tasks:**
1. ✅ Create `serverless_handler.py`
   - Flask API server
   - Stream extraction endpoint
   - Stream relay endpoint
   - Health check
   - Logging system

2. ✅ Create `serverless_requirements.txt`
   - Flask 3.0.0
   - Requests 2.31.0
   - yt-dlp 2024.1.16

3. ✅ Create `do-serverless.yml`
   - Function configuration
   - Environment variables
   - Resource limits
   - Web endpoint config

**Deliverables:**
- Working Flask application
- All endpoints implemented
- Requirements file with all dependencies
- DigitalOcean configuration

---

### Phase 2: CI/CD Pipeline (Hours 2-3)

**Objective:** Set up automated testing and deployment

**Tasks:**
1. ✅ Create `.github/workflows/deploy.yml`
   - Test job (linting + unit tests)
   - Build and deploy job
   - Rollback job on failure
   - Smoke tests

2. ✅ Create `tests/test_serverless_handler.py`
   - Health check test
   - Error handling tests
   - Endpoint validation tests

3. ✅ Create `deploy-to-do.sh`
   - Manual deployment script
   - Authentication setup
   - Function status verification

**Environment Variables:**
- `DIGITALOCEAN_ACCESS_TOKEN` - GitHub Actions secret

**Deliverables:**
- Fully functional CI/CD pipeline
- Automated testing framework
- Deployment scripts
- Rollback capability

---

### Phase 3: User Interface (Hours 3-4)

**Objective:** Create interactive testing UI

**Tasks:**
1. ✅ Create `playground-serverless.js`
   - Updated for serverless endpoints
   - Video ID extraction from URLs
   - Stream fetching and playback
   - Real-time logging
   - Health checks

2. ✅ Update `playground.html` (if needed)
   - Reference serverless JavaScript
   - Endpoint configuration UI

**Features:**
- YouTube video ID parsing
- Stream URL extraction
- Audio player integration
- Endpoint configuration
- Real-time logs
- Error handling and recovery

**Deliverables:**
- Interactive Playground UI
- Complete with audio playback
- Environment configuration options

---

### Phase 4: Documentation & Testing (Hours 4-5)

**Objective:** Complete documentation and final testing

**Tasks:**
1. ✅ Create `DIGITALOCEAN_DEPLOYMENT.md`
   - Comprehensive deployment guide
   - Configuration instructions
   - API reference
   - Troubleshooting guide

2. ✅ Create `DEPLOYMENT_CHECKLIST.md`
   - Pre-deployment checklist
   - Quick start commands
   - Verification steps

3. ✅ Create `.env.example`
   - Environment variable template
   - Configuration documentation

4. ✅ Create `test_serverless_local.py`
   - Local testing script
   - Basic functionality validation

**Deliverables:**
- Complete documentation
- Testing scripts
- Configuration templates
- Deployment checklists

---

## Key Features

### 1. Serverless Architecture
- **Runtime:** Python 3.11
- **Memory:** 512 MB
- **Timeout:** 60 seconds
- **Cost-Effective:** Pay per execution

### 2. API Endpoints

#### Stream Extraction
```
GET /api/stream/{video_id}
Returns: JSON with stream URL, metadata
```

#### Stream Relay
```
GET /streamytlink?url=...
Returns: Video stream (mp4 or other format)
```

#### Health Check
```
GET /health
Returns: {"status": "healthy"}
```

#### Logs Viewer
```
GET /logs
Returns: Recent execution logs
```

### 3. CI/CD Pipeline

**Triggers:**
- On push to main branch
- On pull requests
- Manual workflow dispatch

**Jobs:**
1. **Test** - Linting and unit tests
2. **Deploy** - Build and deploy to DigitalOcean
3. **Smoke Tests** - Verify deployment
4. **Rollback** - Auto-rollback on failure

### 4. Playground UI

**Features:**
- Real-time logging console
- Video ID/URL input
- Stream extraction
- Audio player
- API response inspection
- Health checks
- Endpoint configuration

### 5. Environment Management

**Local Development:**
```bash
python serverless_handler.py
```

**Testing:**
```bash
pytest tests/ -v
python test_serverless_local.py
```

**Deployment:**
```bash
doctl serverless deploy . --remote
```

---

## File Structure

```
project-root/
├── serverless_handler.py              # Main Flask application
├── serverless_requirements.txt        # Python dependencies
├── do-serverless.yml                  # DigitalOcean config
├── test_serverless_local.py           # Local testing
├── deploy-to-do.sh                    # Deployment script
├── playground.html                    # UI template
├── playground-serverless.js           # Updated UI logic
├── .env.example                       # Environment template
├── DIGITALOCEAN_DEPLOYMENT.md         # Deployment guide
├── DEPLOYMENT_CHECKLIST.md            # Pre-deployment checklist
├── .github/
│   └── workflows/
│       └── deploy.yml                 # GitHub Actions CI/CD
├── tests/
│   └── test_serverless_handler.py     # Unit tests
├── api/
│   ├── index.js                       # Existing Node.js API
│   └── proxy.py                       # Existing Python proxy
├── project.yml                        # Existing Node.js config
└── README.md                          # Project documentation
```

---

## Deployment Steps

### Step 1: Prerequisites

```bash
# Install doctl
brew install doctl  # macOS
# or wget for Linux/Windows

# Create DigitalOcean API token
# https://cloud.digitalocean.com/account/api/tokens

# Set environment
export DIGITALOCEAN_ACCESS_TOKEN="dop_v1_..."
```

### Step 2: Local Testing

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r serverless_requirements.txt

# Run tests
python test_serverless_local.py

# Start local server
python serverless_handler.py

# In another terminal, test:
curl http://localhost:8000/health
```

### Step 3: GitHub Setup

```bash
# Create repository
git init
git add .
git commit -m "Initial serverless setup"
git remote add origin https://github.com/your-user/your-repo.git
git push -u origin main
```

### Step 4: Add GitHub Secrets

1. Go to GitHub repository
2. Settings → Secrets and variables → Actions
3. Add `DIGITALOCEAN_ACCESS_TOKEN`
   - Value: Your DigitalOcean API token

### Step 5: Deploy

**Option A: Automatic (GitHub Actions)**
```bash
git push origin main
# Workflow triggers automatically
```

**Option B: Manual (Local)**
```bash
doctl auth init --access-token "$DIGITALOCEAN_ACCESS_TOKEN"
doctl serverless deploy . --remote
```

### Step 6: Verify

```bash
# List functions
doctl serverless functions list

# Get function details
doctl serverless functions get default/stream-extractor

# Test endpoint
curl https://<endpoint>/health
```

---

## API Usage Examples

### Extract Stream URL

```bash
curl -X GET "https://your-function/api/stream/dQw4w9WgXcQ" \
  -H "Accept: application/json"
```

**Response:**
```json
{
  "title": "Rick Astley - Never Gonna Give You Up",
  "url": "https://your-function/streamytlink?url=...",
  "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
  "duration": "212",
  "uploader": "Rick Astley",
  "id": "dQw4w9WgXcQ",
  "ext": "mp4"
}
```

### Stream Relay

```bash
curl -X GET "https://your-function/streamytlink?url=https://example.com/stream.mp4" \
  -H "Range: bytes=0-1024" \
  -o video.mp4
```

### Health Check

```bash
curl https://your-function/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "youtube-stream-url"
}
```

---

## Monitoring & Management

### View Execution Logs

```bash
# Latest activations
doctl serverless activations list --limit 10

# Specific activation details
doctl serverless activations logs <activation-id>
```

### Monitor Performance

- **DigitalOcean Dashboard:** View invocation count, duration, errors
- **GitHub Actions:** Monitor workflow execution
- **Function Logs:** Real-time logging from `/logs` endpoint

### Scaling

DigitalOcean serverless functions auto-scale based on demand:
- **Minimum:** 1 concurrent execution
- **Maximum:** Auto-scales to handle load
- **Idle:** Functions automatically pause when not in use

---

## Security Considerations

### 1. API Token Security
- Store `DIGITALOCEAN_ACCESS_TOKEN` in GitHub Secrets
- Never commit tokens to version control
- Rotate tokens periodically

### 2. CORS Configuration
- All origins allowed (`*`)
- Can be restricted in `do-serverless.yml`
- Adjust based on your security requirements

### 3. Request Validation
- Validate video IDs before processing
- Implement rate limiting (optional)
- Add authentication if needed

### 4. Sensitive Data
- Use DigitalOcean Secrets for sensitive configuration
- Never log sensitive information
- Implement proper error handling

---

## Cost Estimation

### DigitalOcean Functions Pricing
- **Execution Time:** $0.0000002 per GB-second
- **Invocations:** 1 million free per month, then $0.20 per million
- **Example:** 1M requests × 2 seconds × 0.5 GB ≈ $0.20/month

### Typical Monthly Cost
- **Light usage (100K requests):** <$1
- **Medium usage (1M requests):** ~$0.20
- **Heavy usage (10M requests):** ~$20-40

---

## Future Enhancements

### Short Term (v1.0.1)
- [ ] Add authentication/API keys
- [ ] Implement rate limiting
- [ ] Add request caching
- [ ] Enhance error messages

### Medium Term (v1.1)
- [ ] Multi-format output support
- [ ] Spotify integration
- [ ] Advanced search capabilities
- [ ] Custom metadata extraction

### Long Term (v2.0)
- [ ] Database integration
- [ ] User accounts and API keys
- [ ] Analytics dashboard
- [ ] Advanced caching strategy
- [ ] Webhook support

---

## Troubleshooting Guide

### Common Issues & Solutions

**Issue:** Function timeout
```yaml
# Increase timeout in do-serverless.yml
limits:
  timeout: 120000
```

**Issue:** yt-dlp not found
```bash
# Update requirements.txt to include yt-dlp
pip install yt-dlp==2024.1.16
```

**Issue:** CORS errors in browser
```bash
# CORS is enabled by default, check console for exact error
# Verify endpoint URL is correct
```

**Issue:** GitHub Actions fails
1. Check GitHub Actions logs
2. Verify `DIGITALOCEAN_ACCESS_TOKEN` secret
3. Ensure DigitalOcean account is active
4. Check `doctl` version compatibility

---

## Support & Resources

- **DigitalOcean Documentation:** https://docs.digitalocean.com/products/functions/
- **GitHub Actions Documentation:** https://docs.github.com/en/actions
- **doctl CLI Reference:** https://docs.digitalocean.com/reference/doctl/
- **yt-dlp Documentation:** https://github.com/yt-dlp/yt-dlp
- **Flask Documentation:** https://flask.palletsprojects.com/

---

## Maintenance Schedule

### Daily
- Monitor function logs
- Track error rates
- Validate health checks

### Weekly
- Review performance metrics
- Update dependencies if needed
- Check for security updates

### Monthly
- Audit API usage
- Review cost reports
- Update documentation
- Plan enhancements

---

## Conclusion

This advanced plan provides a complete, production-ready serverless solution for YouTube stream URL extraction on DigitalOcean with:

✅ Automated CI/CD pipeline  
✅ Comprehensive testing framework  
✅ Interactive Playground UI  
✅ Complete documentation  
✅ Auto-scaling and monitoring  
✅ Cost-effective deployment  
✅ Security best practices  

The solution is ready for deployment and can handle production workloads with minimal operational overhead.
