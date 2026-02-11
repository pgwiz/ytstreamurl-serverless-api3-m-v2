#!/bin/bash
set -e

# Build script for DigitalOcean Functions (Python 3.11)
# Install Python requirements into a local 'vendor' directory using --target
# so only site-packages are included (avoids creating a full virtualenv which can be large).

PY="$(which python || which python3 || echo python)"
$PY -m pip install --upgrade pip
# Install into ./vendor (site-packages) to keep package size small
rm -rf vendor
python -m pip install --upgrade pip
python -m pip install --no-cache-dir --target ./vendor -r requirements.txt

# Ensure files are present for deployment
echo "Build complete"