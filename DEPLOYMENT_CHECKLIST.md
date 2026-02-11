# Pre-Deployment Checklist

## Local Development Setup
- [ ] Python 3.11 installed
- [ ] Virtual environment created (`python3.11 -m venv venv`)
- [ ] Dependencies installed (`pip install -r serverless_requirements.txt`)
- [ ] Local tests pass (`python test_serverless_local.py`)
- [ ] Flask server runs locally (`python serverless_handler.py`)
- [ ] Health check works (`curl http://localhost:8000/health`)

## Git & GitHub Setup
- [ ] Repository initialized with git
- [ ] Code committed to main branch
- [ ] GitHub repository created
- [ ] Branch protection rules configured (optional)

## DigitalOcean Account Setup
- [ ] DigitalOcean account created
- [ ] API token generated
- [ ] doctl CLI installed
- [ ] doctl authenticated (`doctl auth init`)
- [ ] DigitalOcean connection verified (`doctl account get`)

## GitHub Actions Secrets
- [ ] `DIGITALOCEAN_ACCESS_TOKEN` secret added
  - Go to: Repository → Settings → Secrets and variables → Actions
  - Click "New repository secret"
  - Name: `DIGITALOCEAN_ACCESS_TOKEN`
  - Value: Your DigitalOcean API token

## Configuration Files Verified
- [ ] `do-serverless.yml` - Properly configured
- [ ] `serverless_handler.py` - Main handler ready
- [ ] `serverless_requirements.txt` - All dependencies listed
- [ ] `.github/workflows/deploy.yml` - Workflow configured
- [ ] `.env.example` - Template created

## Deployment Preparation
- [ ] README.md updated with serverless info
- [ ] DIGITALOCEAN_DEPLOYMENT.md reviewed
- [ ] API documentation reviewed
- [ ] Test video ID available (e.g., dQw4w9WgXcQ)

## First Deployment
- [ ] Push to main branch
- [ ] GitHub Actions workflow starts automatically
- [ ] Monitor workflow execution
- [ ] Verify deployment success
- [ ] Test serverless endpoint with cURL
- [ ] Test with Playground UI

## Post-Deployment
- [ ] Function logs accessible and working
- [ ] Health endpoint responding
- [ ] Stream extraction working
- [ ] CORS headers present in responses
- [ ] Monitoring and alerts configured (optional)

## Documentation
- [ ] Deployment guide reviewed
- [ ] API documentation available
- [ ] Troubleshooting guide examined
- [ ] Team members notified

---

## Quick Start Commands

```bash
# 1. Local testing
python test_serverless_local.py

# 2. Local development
python serverless_handler.py

# 3. Authentication
export DIGITALOCEAN_ACCESS_TOKEN="your_token"
doctl auth init --access-token "$DIGITALOCEAN_ACCESS_TOKEN"

# 4. Deploy locally
doctl serverless deploy . --remote

# 5. Verify deployment
doctl serverless functions list
doctl serverless functions get default/stream-extractor

# 6. Test endpoint
curl https://<your-endpoint>/health
```

---

## Support Resources

- DigitalOcean Functions Docs: https://docs.digitalocean.com/products/functions/
- GitHub Actions Docs: https://docs.github.com/en/actions
- doctl CLI Reference: https://docs.digitalocean.com/reference/doctl/
