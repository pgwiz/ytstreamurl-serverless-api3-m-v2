#!/bin/bash
set -e

# Build script for DigitalOcean Functions (Python 3.11)
# Create a virtual environment and install requirements into it so they are packaged

PY="$(which python || which python3 || echo python)"
$PY -m pip install --upgrade pip
$PY -m venv virtualenv
# Activate venv and install into site-packages
. virtualenv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt --no-cache-dir

# Ensure files are present for deployment
echo "Build complete"