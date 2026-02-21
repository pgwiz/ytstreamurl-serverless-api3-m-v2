# YouTube Stream Extractor - Docker Edition

A complete YouTube stream extraction API with web playground UI, packaged for Docker deployment on Render, Koyeb, or any cloud platform.

**Features:**
- ✅ Extract YouTube stream URLs using yt-dlp + Node.js
- ✅ YouTube search functionality
- ✅ Interactive web playground UI
- ✅ RESTful API with JSON responses
- ✅ Cookie support for authentication
- ✅ Production-ready with health checks and logging

## Quick Start

### Local Testing with Docker Compose

```bash
# Build the image
docker-compose build

# Start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

The app will be available at `http://localhost:5000`

### Manual Docker Build & Run

```bash
# Build image
docker build -t youtube-stream-api .

# Run container
docker run -d -p 5000:5000 \
  -e PORT=5000 \
  -e ENV=production \
  --name youtube-stream-api \
  youtube-stream-api

# View logs
docker logs -f youtube-stream-api

# Stop container
docker stop youtube-stream-api
```

## Cloud Deployment

### Deploy to Render

1. **Connect Repository**
   - Go to https://dashboard.render.com
   - Click "Create" → "Web Service"
   - Connect your GitHub repository
   
2. **Configure Service**
   - Name: `youtube-stream-api`
   - Environment: `Docker`
   - Region: Choose closest to you
   - Plan: Free tier available
   
3. **Build & Deploy**
   - Render will automatically detect `Dockerfile`
   - Build and deploy on every push

4. **Environment Variables** (optional)
   - `PORT`: 5000 (auto-set by Render)
   - `ENV`: production
   - `REQUEST_TIMEOUT`: 60

### Deploy to Koyeb

1. **Connect Repository**
   - Go to https://app.koyeb.com
   - Click "Deploy" → "GitHub"
   - Select repository
   
2. **Configure Build**
   - Buildpack: `Docker`
   - Port: `5000`
   
3. **Deploy**
   - Hit deploy and wait 5-10 minutes
   - Get your public URL

4. **Environment Variables** (optional)
   - `PORT`: 8000 (default Koyeb port) - can be changed to 5000
   - `ENV`: production

## API Endpoints

### Get Stream URL
```bash
GET /api/stream/<video_id>
```
Returns stream URL and metadata for a YouTube video.

**Example:**
```bash
curl https://your-domain.com/api/stream/dQw4w9WgXcQ
```

**Response:**
```json
{
  "title": "Rick Astley - Never Gonna Give You Up",
  "url": "https://...",
  "thumbnail": "https://...",
  "duration": 212,
  "uploader": "Rick Astley",
  "view_count": 1234567890,
  "videoId": "dQw4w9WgXcQ",
  "ext": "mp4"
}
```

### Search YouTube
```bash
GET /api/search/youtube?q=<query>&limit=<count>
```
Search YouTube videos.

**Example:**
```bash
curl "https://your-domain.com/api/search/youtube?q=python&limit=5"
```

### API Status
```bash
GET /api/status
```
Get system status including Node.js and cookie availability.

## Cookies Support

To use authentication cookies (for private/restricted videos):

1. Export cookies from YouTube using browser extension
2. Save as `cookies.txt` in the `docker_pie/` directory
3. Mount during deployment:
   ```bash
   docker run -v ./cookies.txt:/tmp/cookies.txt:ro youtube-stream-api
   ```

## Requirements

- Docker 20.10+
- Python 3.11
- Node.js (installed in container)
- ~500MB disk space for Docker image

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| PORT | 5000 | HTTP server port |
| ENV | development | Set to `production` for gunicorn |
| LOG_DIR | /tmp/proxyLogs | Logging directory |
| REQUEST_TIMEOUT | 60 | yt-dlp extraction timeout (seconds) |
| COOKIES_FILE | /tmp/cookies.txt | Path to YouTube cookies |

## File Structure

```
docker_pie/
├── Dockerfile           # Multi-stage Docker build
├── docker-compose.yml   # Local development compose
├── requirements.txt     # Python dependencies
├── app.py              # Flask API server
├── .dockerignore        # Docker build exclusions
└── static/
    ├── playground.html  # Web UI
    └── playground.js    # Frontend logic
```

## Troubleshooting

### Issue: "JS runtimes: none"
The Node.js installation failed. This is common in some cloud environments. Try:
1. Use Render (has better build environment)
2. Or rebuild the Docker image locally and push

### Issue: Videos fail to extract
1. Check if video is region-restricted
2. Try uploading cookies.txt
3. Increase REQUEST_TIMEOUT environment variable

### Issue: Port already in use
Change the port binding:
```bash
docker run -p 8000:5000 youtube-stream-api
```
Then access at `http://localhost:8000`

## Performance Tips

- First request takes 10-30 seconds (cold start)
- Subsequent requests are faster (~5-10 seconds)
- Use production environment (`ENV=production`) for better performance
- Consider a larger plan if running many parallel extractions

## Limits

- Render Free: 0.5 GB RAM, limited bandwidth
- Koyeb Free: Sharable compute, limited requests
- Both platforms: 4-hour timeout limit

For production use, consider Pro plans or self-hosting.

## Support

For issues with yt-dlp: https://github.com/yt-dlp/yt-dlp
For Docker questions: https://docs.docker.com

## License

MIT
