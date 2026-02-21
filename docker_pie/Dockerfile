# Multi-stage build for YouTube stream extraction API with playground UI
# Build date: 2026-02-22 (force rebuild)
FROM node:20-alpine AS js-base
WORKDIR /app

# Install Node.js dependencies if needed
RUN npm install -g npm@latest

# Main Python runtime
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js for yt-dlp JavaScript runtime
# Use nodejs from official repo for better compatibility
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    jq \
    ca-certificates \
    gnupg \
    lsb-release \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Verify Node.js installation
RUN which node && node --version && npm --version

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY youtube_extractor.py .
COPY static ./static/

# Copy cookies if available - try both locations
COPY cookies.txt /app/cookies.txt 2>/dev/null || true
RUN test -f /app/cookies.txt || echo "INFO: No cookies.txt in docker_pie - will check runtime paths"

# Create necessary directories
RUN mkdir -p /tmp/proxyLogs /tmp/videos

# Set environment variables
ENV PORT=5000 \
    COOKIES_FILE=/app/cookies.txt \
    LOG_DIR=/tmp/proxyLogs \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/health || exit 1
