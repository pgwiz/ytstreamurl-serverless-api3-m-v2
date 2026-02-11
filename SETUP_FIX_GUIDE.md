# ⚡ Project Structure Fix & Setup Guide

## What Changed

Your project structure has been updated to match **DigitalOcean Functions strict requirements**.

### New Structure

```
ytstreamurl-serverless-api3-m-v2/
├── project.yml                          ✅ Updated to match DO spec
├── packages/
│   └── default/                         ✅ Required: package directory
│       └── (functions go here)
├── serverless_handler.py                📍 Entry point handler
├── serverless_requirements.txt
├── DOCTL_COMPREHENSIVE_GUIDE.md         ✨ NEW: Complete doctl reference
└── ... (other files)
```

### Key Improvements

✅ **project.yml updated:**
- Uses proper `packages/` structure
- Specifies `main: serverless_handler:app` (Flask app entry point)
- Sets `runtime: python:3.11` 
- Increases timeout to 60 seconds
- Sets memory to 512 MB

✅ **Directory structure created:**
- `packages/default/` created (required for doctl)

✅ **New documentation:**
- `DOCTL_COMPREHENSIVE_GUIDE.md` - extensive doctl reference

---

## Important Setup Step

### Move Handler to Correct Location

The `serverless_handler.py` needs to be in the `packages/default/` directory for DigitalOcean to find it.

**Option 1: Copy the file**
```bash
cp serverless_handler.py packages/default/serverless_handler.py
```

**Option 2: Create symlink (Linux/macOS)**
```bash
ln -s ../serverless_handler.py packages/default/serverless_handler.py
```

**Option 3: Just edit project.yml to reference the root**
```yaml
main: ../serverless_handler:app
```

**I recommend Option 1** - copy the file so there are no path issues.

---

## Verification Checklist

Before deploying, verify structure:

```bash
# Check project.yml exists
$ ls -la project.yml
project.yml

# Check packages directory
$ ls -la packages/
default/

# Check serverless_handler.py exists in packages/default
$ ls -la packages/default/
serverless_handler.py

# Verify project.yml syntax
$ doctl serverless validate .
Validation successful!

# Connect to namespace
$ doctl serverless connect fn-bb05ab8d-3ad1-453e-a3ef-da38e7e0d078

# Deploy
$ doctl serverless deploy .
```

---

## Complete doctl Workflow

Now that you understand doctl completely (from the guide), here's the recommended flow:

### Local Development
```bash
# 1. Install dependencies
pip install -r serverless_requirements.txt

# 2. Run local tests
python test_serverless_local.py

# 3. Start dev server
python serverless_handler.py

# 4. Open playground
# http://localhost:8000/playground
```

### Before Deployment
```bash
# 5. Lint code
flake8 serverless_handler.py

# 6. Run unit tests
pytest tests/ -v

# 7. Validate project structure
doctl serverless validate .
```

### Deploy to DigitalOcean
```bash
# 8. Authenticate
doctl auth init --access-token "YOUR_TOKEN"

# 9. Install serverless support
doctl serverless install

# 10. Connect to namespace
doctl serverless connect fn-bb05ab8d-3ad1-453e-a3ef-da38e7e0d078

# 11. Deploy!
doctl serverless deploy .

# 12. Check deployment
doctl serverless functions list
```

### Monitor & Debug
```bash
# View recent executions
doctl serverless activations list

# View specific logs
doctl serverless activations logs <activation-id>

# Invoke function
doctl serverless functions invoke default/stream-extractor
```

---

## Understanding project.yml

Your updated `project.yml`:

```yaml
name: youtube-stream-url                    # Project name
description: YouTube stream URL extraction

packages:
  - name: default                           # Package name → accessed as "default/function"
    environment:                            # Environment vars for all functions in package
      PYTHONUNBUFFERED: "1"
      YT_DLP_PATH: /usr/local/bin/yt-dlp
    
    functions:
      - name: stream-extractor              # Function name → accessed as "default/stream-extractor"
        main: serverless_handler:app        # Entry point: file:function_name
        runtime: python:3.11                # Python 3.11 runtime
        web: true                           # HTTP accessible
        limits:
          timeout: 60000                    # 60 seconds max
          memory: 512                       # 512 MB max
```

---

## Common Errors (Now You Know!)

Read `DOCTL_COMPREHENSIVE_GUIDE.md` for:

✅ "serverless support is not installed"
→ Solution: `doctl serverless install`

✅ "not connected to a functions namespace"
→ Solution: `doctl serverless connect <namespace-id>`

✅ "project.yml not found"
→ Solution: Must run `doctl serverless deploy .` from project root

✅ "packages directory not found"
→ Solution: Create `packages/` directory with function subdirectories

✅ "No matching distribution found"
→ Solution: Use flexible version constraints (e.g., `yt-dlp` not `yt-dlp==2024.1.16`)

✅ "function not found"
→ Solution: Use correct format: `doctl serverless functions invoke default/stream-extractor`

And many more... see the guide!

---

## GitHub Actions Workflow (Now Ready!)

Your `.github/workflows/deploy.yml` is already configured with:

✅ Python linting step  
✅ Unit tests  
✅ Official doctl GitHub Action  
✅ Serverless support installation  
✅ Namespace connection  
✅ Project validation  
✅ Deployment  
✅ Smoke tests  
✅ Auto-rollback on failure  

Just ensure GitHub secret is set:
```
Repository → Settings → Secrets and variables → Actions
DIGITALOCEAN_ACCESS_TOKEN = your_token_here
```

---

## Files Changed

| File | Change | Status |
|------|--------|--------|
| `project.yml` | Updated to DigitalOcean spec | ✅ |
| `serverless_handler.py` | No change needed | ✅ |
| `packages/default/` | Created directory | ✅ |
| `DOCTL_COMPREHENSIVE_GUIDE.md` | **NEW: Complete reference** | ✅ |
| `.github/workflows/deploy.yml` | Already configured | ✅ |

---

## Next Steps

1. ✅ **Copy or move** `serverless_handler.py` to `packages/default/`
2. ✅ **Read** `DOCTL_COMPREHENSIVE_GUIDE.md` for comprehensive understanding
3. ✅ **Test locally** with `python test_serverless_local.py`
4. ✅ **Validate** with `doctl serverless validate .`
5. ✅ **Deploy** with `doctl serverless deploy .`

---

## You Now Have

📚 **Complete Understanding of:**
- How doctl works
- Project structure requirements
- project.yml configuration
- Common errors & solutions
- Best practices
- CI/CD workflow
- Troubleshooting guide

🚀 **Ready to:**
- Deploy to production
- Handle errors with confidence
- Understand what went wrong
- Fix issues quickly

---

**Read:** `DOCTL_COMPREHENSIVE_GUIDE.md` for the complete reference!
