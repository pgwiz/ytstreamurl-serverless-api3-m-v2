# Comprehensive doctl & DigitalOcean Functions Guide

## Table of Contents
1. [doctl Essentials](#essentials)
2. [Project Structure Requirements](#project-structure)
3. [Project Configuration (project.yml)](#project-configuration)
4. [Common Errors & Solutions](#common-errors)
5. [Best Practices](#best-practices)
6. [CI/CD Workflow Guide](#ci-cd-workflow)
7. [Troubleshooting Checklist](#troubleshooting)

---

## Essentials

### What is doctl?

**doctl** is the official DigitalOcean CLI (Command Line Interface) that allows you to manage all DigitalOcean resources from the terminal, including:
- Droplets
- Kubernetes clusters
- Firewalls, load balancers
- **Functions (Serverless)** ← What we're using

### Key doctl Serverless Commands

```bash
# Authentication
doctl auth init --access-token "YOUR_TOKEN"
doctl account get                              # Verify connection

# Serverless extension
doctl serverless install                       # Install serverless support
doctl serverless status                        # Check status

# Namespace management
doctl serverless namespaces list               # List all namespaces
doctl serverless namespaces create --label my-ns --region nyc1
doctl serverless connect <namespace-id>       # Connect to namespace

# Function operations
doctl serverless deploy .                      # Deploy project in current dir
doctl serverless deploy <path>                 # Deploy specific path
doctl serverless functions list                # List deployed functions
doctl serverless functions get <pkg>/<func>   # Get function details
doctl serverless functions invoke <pkg>/<func># Invoke a function
doctl serverless functions delete <pkg>/<func># Delete function

# Logs & debugging
doctl serverless activations list              # List recent executions
doctl serverless activations logs <id>        # View logs for activation
```

---

## Project Structure

### Required Directory Layout

DigitalOcean Functions requires a **STRICT** project structure:

```
your-project/
├── project.yml                    # REQUIRED: Configuration file
└── packages/                      # REQUIRED: Directory containing packages
    └── package-name/              # Package directory
        ├── function1.py           # Single-file function
        ├── function2/             # Multi-file function
        │   ├── __main__.py        # Entry point (Python)
        │   └── helper.py
        └── function3.js           # Node.js function
```

### Important Rules

1. **Must have `project.yml`** at project root
2. **Must have `packages/` directory** at project root
3. **Minimum 1 package** in packages/ directory
4. **Minimum 1 function** per package
5. Functions are accessed as: `package-name/function-name`

### Example Structure

```
youtube-stream-url/
├── project.yml
├── packages/
│   ├── default/                   # Package name
│   │   ├── stream-extractor.py    # Function 1
│   │   ├── stream-relay.py        # Function 2
│   │   └── health-check.py        # Function 3
```

---

## Project Configuration

### project.yml Structure

The `project.yml` file defines how functions are deployed:

```yaml
# Top-level: applies to all packages/functions
environment:
  ENV: production
  
packages:
  - name: default                  # Package name
    environment:
      LOG_LEVEL: info
      
    functions:
      - name: stream-extractor      # Function name
        main: stream-extractor:app  # entry_file:function_name
        runtime: python:3.11
        web: true                   # Make it accessible via HTTP
        limits:
          timeout: 60000            # milliseconds
          memory: 512               # MB
        environment:
          YT_DLP_PATH: /usr/local/bin/yt-dlp
```

### Key Properties

| Property | Level | Description |
|----------|-------|-------------|
| `name` | Package/Function | Package or function identifier |
| `main` | Function | Entry point (format: `file:function`) |
| `runtime` | Function | Language runtime (python:3.11, nodejs:18, etc) |
| `web` | Function | Boolean - make HTTP accessible |
| `timeout` | Function | Max execution time in milliseconds |
| `memory` | Function | RAM allocation in MB |
| `environment` | Any | Environment variables for functions |
| `limits` | Function | Resource constraints (timeout, memory, logs) |

### Entry Point Format

For Python functions:
```python
# file: my_function.py
def app(args):
    return {"message": "Hello"}
```

In project.yml:
```yaml
main: my_function:app  # filename:function_name
```

---

## Common Errors & Solutions

### Error 1: "serverless support is not installed"

**Problem:** You haven't installed the serverless plugin for doctl

**Solution:**
```bash
doctl serverless install
```

**In CI/CD:**
```yaml
- name: Install DigitalOcean Serverless support
  run: doctl serverless install
```

---

### Error 2: "serverless support is installed but not connected to a functions namespace"

**Problem:** doctl is installed but not connected to a namespace

**Solution:**
```bash
doctl serverless connect <namespace-id>

# Example:
doctl serverless connect fn-bb05ab8d-3ad1-453e-a3ef-da38e7e0d078
```

**In CI/CD:**
```yaml
- name: Connect to DigitalOcean Functions namespace
  run: doctl serverless connect fn-bb05ab8d-3ad1-453e-a3ef-da38e7e0d078
```

---

### Error 3: "project.yml not found"

**Problem:** doctl can't find the configuration file

**Solution:**
1. Make sure `project.yml` exists in project root
2. Run `doctl serverless deploy` from project root:
```bash
cd /path/to/project
doctl serverless deploy .
```

3. Or specify the path:
```bash
doctl serverless deploy /path/to/project
```

---

### Error 4: "packages/ directory not found"

**Problem:** Project structure is wrong

**Solution:**
```
project/
├── project.yml
└── packages/
    └── default/
        └── my-function.py
```

NOT:
```
project/
├── project.yml
└── my-function.py       ❌ WRONG - must be in packages/
```

---

### Error 5: "No matching distribution found for yt-dlp==2024.1.16"

**Problem:** Specific version doesn't exist on PyPI

**Solution:**
- Use flexible version: `yt-dlp>=2024.01.01`
- Or just: `yt-dlp` (latest)

In requirements.txt:
```
flask==3.0.0
requests==2.31.0
yt-dlp          # Use latest
```

---

### Error 6: "function Not Found" when invoking

**Problem:** Format is wrong or function doesn't exist

**Correct Format:**
```bash
doctl serverless functions invoke package-name/function-name
```

**Example:**
```bash
doctl serverless functions invoke default/stream-extractor
```

NOT: `doctl serverless functions invoke stream-extractor` ❌

---

### Error 7: Node version compatibility

**Problem:** Selected Node.js runtime doesn't have required modules

**Solution:**
- Use supported versions: `nodejs:18`, `nodejs:20`, `nodejs:default`
- Install with npm/yarn before deploying
- Include package.json AND package-lock.json

---

## Best Practices

### 1. Project Organization

✅ **Good:**
```
project/
├── project.yml
├── packages/
│   ├── api/
│   │   ├── stream-extractor/
│   │   │   ├── __main__.py
│   │   │   └── helpers.py
│   │   └── health-check.py
│   └── utils/
│       └── logger.py
├── requirements.txt
└── .env.example
```

❌ **Bad:**
```
project/
├── stream-extractor.py
└── requirements.txt
# Missing: project.yml, packages/ directory
```

### 2. Environment Variables

**Static in project.yml:**
```yaml
environment:
  LOG_LEVEL: info
  REGION: nyc3
```

**Dynamic from .env:**
```bash
# .env file
DATABASE_URL=postgres://...
API_KEY=secret123
```

```yaml
environment:
  DATABASE_URL: "${DATABASE_URL}"
  API_KEY: "${API_KEY}"
```

Deploy with:
```bash
doctl serverless deploy . --env .env
```

### 3. Resource Limits

Set appropriate limits based on your function:

```yaml
functions:
  - name: lightweight-task
    limits:
      timeout: 10000      # 10 seconds
      memory: 128         # 128 MB
  
  - name: heavy-processing
    limits:
      timeout: 60000      # 60 seconds
      memory: 512         # 512 MB
```

### 4. Web Functions

Make functions HTTP-accessible:

```yaml
functions:
  - name: api-endpoint
    web: true             # Enable HTTP access
    webSecure: "secret"   # Optional: require auth
```

Invoke web functions without doctl:
```bash
curl https://<endpoint>/api/<package>/<function>
```

### 5. Local Testing

Always test before deploying:

```bash
# Test locally (if Flask-based)
python serverless_handler.py

# Run unit tests
pytest tests/ -v

# Lint code
flake8 serverless_handler.py

# Then deploy
doctl serverless deploy .
```

### 6. Logging & Debugging

Use proper logging:

```python
import sys

def app(args):
    print("Starting function...", file=sys.stdout, flush=True)
    print("Error message", file=sys.stderr, flush=True)
    return {"status": "ok"}
```

View logs:
```bash
doctl serverless activations list
doctl serverless activations logs <activation-id>
```

---

## CI/CD Workflow Guide

### Complete GitHub Actions Workflow

```yaml
name: Deploy DigitalOcean Serverless

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      # 1. Checkout code
      - name: Checkout code
        uses: actions/checkout@v4

      # 2. Set up Python (for linting/testing)
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      # 3. Install dependencies for testing
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r serverless_requirements.txt
          pip install flake8 pytest

      # 4. Lint code
      - name: Lint with flake8
        run: |
          flake8 serverless_handler.py --max-line-length=127

      # 5. Run tests
      - name: Run tests
        run: pytest tests/ -v || true

      # 6. Set up doctl (official)
      - name: Set up DigitalOcean CLI
        uses: digitalocean/action-doctl@v2
        with:
          token: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}

      # 7. Install serverless support
      - name: Install serverless support
        run: doctl serverless install

      # 8. Connect to namespace
      - name: Connect to namespace
        run: doctl serverless connect fn-bb05ab8d-3ad1-453e-a3ef-da38e7e0d078

      # 9. Validate configuration
      - name: Validate project configuration
        run: |
          doctl serverless status
          doctl serverless validate . || true

      # 10. Deploy
      - name: Deploy to DigitalOcean Functions
        run: doctl serverless deploy . --remote

      # 11. Smoke test
      - name: Smoke test
        run: |
          sleep 5
          doctl serverless functions list
```

### Required GitHub Secrets

In GitHub repository settings:

```
DIGITALOCEAN_ACCESS_TOKEN = dop_v1_xxxxxxxxxxxx
```

---

## Troubleshooting Checklist

### Before Deployment

- [ ] Does `project.yml` exist in project root?
- [ ] Does `packages/` directory exist?
- [ ] Does each package have at least one function?
- [ ] Is the function entry point correct (file:function)?
- [ ] Does runtime match available options?
- [ ] Are all dependencies listed in requirements.txt?
- [ ] Do you have a valid DigitalOcean API token?
- [ ] Is the namespace ID correct?

### Authentication Issues

```bash
# Check if authenticated
doctl auth list

# Re-authenticate
doctl auth init --access-token "YOUR_TOKEN"

# Verify token
doctl account get
```

### Namespace Connection

```bash
# Check current namespace
doctl serverless status

# List available namespaces
doctl serverless namespaces list

# Connect to specific namespace
doctl serverless connect <namespace-id>
```

### Function Deployment

```bash
# Validate project
doctl serverless validate .

# Deploy with verbose output
doctl serverless deploy . --remote

# Check deployed functions
doctl serverless functions list

# Get function details
doctl serverless functions get default/stream-extractor
```

### Debugging

```bash
# Get recent activations
doctl serverless activations list --limit 10

# Get specific activation logs
doctl serverless activations logs <activation-id>

# Invoke function with parameters
doctl serverless functions invoke default/stream-extractor -p video_id:dQw4w9WgXcQ
```

---

## Quick Reference Commands

```bash
# Setup
doctl auth init --access-token "TOKEN"
doctl serverless install
doctl serverless connect <namespace-id>

# Development
doctl serverless deploy .                    # Deploy from current dir
doctl serverless validate .                  # Validate project

# Operations
doctl serverless functions list              # List functions
doctl serverless functions invoke <pkg>/<fn># Run function
doctl serverless activations list            # View recent runs
doctl serverless activations logs <id>      # View logs

# Cleanup
doctl serverless functions delete <pkg>/<fn># Delete function
doctl serverless undeploy <pkg>/<fn>        # Undeploy function
```

---

## Key Takeaways

1. **Structure matters** - Must follow `project.yml` + `packages/` layout
2. **Namespace required** - Always connect before deploying
3. **Version careful** - Pin compatible versions or use flexible constraints
4. **Test locally** - Use linting and unit tests before pushing
5. **Environment variables** - Configure in project.yml, not hardcoded
6. **Logs are helpful** - Always check activation logs for debugging
7. **Resource limits** - Set appropriate timeout/memory for your functions
8. **CI/CD automated** - Use official `digitalocean/action-doctl` action

---

**Generated:** February 11, 2026  
**Last Updated:** Based on DigitalOcean Docs (Jan 2026)
