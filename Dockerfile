# Root-level Dockerfile that builds from docker_pie folder
# Usage: docker build -f Dockerfile -t youtube-stream-api .

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js for yt-dlp JavaScript runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    jq \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements from docker_pie
COPY docker_pie/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files from docker_pie
COPY docker_pie/app.py .
COPY docker_pie/static ./static/

# Create necessary directories
RUN mkdir -p /tmp/proxyLogs /tmp/videos

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/ || exit 1

# Expose port (use Render/Koyeb PORT env var)
ENV PORT=5000
EXPOSE 5000

# Start the application
CMD ["sh", "-c", "python app.py ${PORT:-5000}"]
