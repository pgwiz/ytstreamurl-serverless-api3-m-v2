#!/bin/bash
set -e

# Build script for DigitalOcean Functions (Python 3.11)
# Creates virtualenv and installs requirements into runtime-specific location.

# Create virtualenv without pip to keep small
virtualenv --without-pip virtualenv

# Install requirements into the correct site-packages for Python 3.11
pip install -r requirements.txt --target virtualenv/lib/python3.11/site-packages

# Ensure files are present for deployment
echo "Build complete"
