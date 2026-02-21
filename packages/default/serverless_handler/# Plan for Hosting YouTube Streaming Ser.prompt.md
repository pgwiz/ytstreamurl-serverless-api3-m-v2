# Plan for Hosting YouTube Streaming Serverless Function on DigitalOcean with CI/CD Pipeline

## Overview
This plan outlines the steps to:
1. Create a serverless function for the `simple_proxy.py` script.
2. Deploy the serverless function on DigitalOcean using `dotctl`.
3. Set up a CI/CD pipeline on GitHub for automated deployment.
4. Optionally integrate the Playground UI for testing and interaction.

---

## Step 1: Create the Serverless Function

### Requirements:
- DigitalOcean CLI (`dotctl`) installed and authenticated.
- Python runtime support for the serverless function.

### Implementation:
1. Refactor `simple_proxy.py` to ensure it is stateless and suitable for serverless execution.
2. Create a `requirements.txt` file listing all dependencies.
3. Package the function for deployment:
   - Ensure the entry point is clearly defined (e.g., `app` or `handler`).

---

## Step 2: DigitalOcean Project Configuration YAML File

### File: `project.yml`
This file defines the serverless function configuration for DigitalOcean.

```yaml
name: youtube-stream-url
region: nyc3
runtime: python3.9
entrypoint: simple_proxy:app
routes:
  - path: /stream-url
    method: POST
    function: simple_proxy
```

---

## Step 3: CI/CD Pipeline with GitHub Actions

### File: `.github/workflows/deploy.yml`
This workflow automates the deployment process.

```yaml
name: Deploy to DigitalOcean

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Authenticate with DigitalOcean
      env:
        DOTCTL_API_TOKEN: ${{ secrets.DIGITALOCEAN_API_TOKEN }}
      run: |
        dotctl auth init

    - name: Deploy to DigitalOcean
      run: |
        dotctl deploy --config project.yml
```

---

## Step 4: Optional Playground UI Integration

### Steps:
1. Modify the `playground.html` file to include a form for testing the serverless function.
2. Update the JavaScript (`playground.js`) to send requests to the deployed serverless function endpoint.
3. Ensure the UI dynamically displays the response from the serverless function.

---

## Advanced Considerations
- **Monitoring:** Use DigitalOcean's monitoring tools to track function performance.
- **Scaling:** Configure auto-scaling for the serverless function based on traffic.
- **Security:** Secure the API endpoint with authentication (e.g., API keys).
- **Testing:** Implement unit and integration tests for the `simple_proxy.py` function.

---

## Next Steps
1. Refactor `simple_proxy.py` for serverless compatibility.
2. Create the `project.yml` file.
3. Set up the GitHub Actions workflow.
4. Deploy and test the serverless function.
5. Optionally integrate the Playground UI for enhanced usability.
