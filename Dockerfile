# Root-level Dockerfile that builds from docker_pie folder
# Usage: docker build -f Dockerfile -t youtube-stream-api .
# Build ID: 2026-02-22-22-30-Z-INLINED-APP-NO-IMPORTS-CACHE-BUST-12345

FROM python:3.11-slim

WORKDIR /app

# Force cache bust with unique marker
RUN echo "Build: inlined app.py with no external imports requirement"

# Install system dependencies including Node.js for yt-dlp JavaScript runtime
# Use NodeSource official repo for better compatibility
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

# Copy Python requirements from docker_pie
COPY docker_pie/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files from docker_pie
COPY docker_pie/app.py .
COPY docker_pie/static ./static/

# Copy cookies if available
COPY docker_pie/cookies.txt /app/cookies.txt
RUN ls -lah /app/cookies.txt || echo "⚠️ WARNING: cookies.txt not copied"

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

# Expose port
EXPOSE 5000

# Start the application
CMD ["sh", "-c", "python app.py ${PORT:-5000}"]
