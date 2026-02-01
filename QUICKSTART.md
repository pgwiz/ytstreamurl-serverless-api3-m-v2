# Quick Start: Digital Ocean Serverless YouTube Downloader

This guide will help you quickly deploy the YouTube downloader to Digital Ocean Functions.

## Prerequisites

1. **Digital Ocean Account**: Sign up at [digitalocean.com](https://www.digitalocean.com/)
2. **doctl CLI**: Install the Digital Ocean CLI tool

### Install doctl

**macOS:**
```bash
brew install doctl
```

**Linux:**
```bash
cd ~
wget https://github.com/digitalocean/doctl/releases/download/v1.94.0/doctl-1.94.0-linux-amd64.tar.gz
tar xf ~/doctl-1.94.0-linux-amd64.tar.gz
sudo mv ~/doctl /usr/local/bin
```

**Windows:**
Download from [GitHub Releases](https://github.com/digitalocean/doctl/releases)

## Setup Steps

### 1. Authenticate with Digital Ocean

```bash
doctl auth init
```

Enter your Digital Ocean API token when prompted.

### 2. Enable Functions (One-time)

```bash
doctl serverless install
doctl serverless connect
```

### 3. Deploy the Function

```bash
# Navigate to project root
cd /path/to/ytstreamurl-serverless-api3-m-v2

# Deploy
doctl serverless deploy .
```

### 4. Get Your Function URL

```bash
doctl serverless functions list
```

You'll see output like:
```
FUNCTION     RUNTIME    LIMIT (MB)  TIMEOUT (MS)  WEB  INSTANCES
youtube      nodejs:18  256         30000         yes  0
```

Get the URL:
```bash
doctl serverless functions get youtube --url
```

Example output:
```
https://faas-nyc1-2ef2e6cc.doserverless.co/api/v1/web/fn-XXXXX/youtube
```

## Using the Function

### Test via cURL

```bash
curl "https://YOUR-FUNCTION-URL?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=video"
```

### Use the Web UI

1. Open `youtube-downloader.html` in a text editor
2. Update the `API_URL` constant:
   ```javascript
   const API_URL = 'https://YOUR-FUNCTION-URL';
   ```
3. Host the HTML file on:
   - GitHub Pages
   - Netlify
   - Vercel
   - Or any web hosting

## Example Usage

### Get Video (Highest Quality)
```bash
curl "https://YOUR-FUNCTION-URL?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=video&quality=highest"
```

### Get Audio Only
```bash
curl "https://YOUR-FUNCTION-URL?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=audio&quality=highest"
```

## Response Format

```json
{
  "success": true,
  "videoId": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up",
  "author": "Rick Astley",
  "lengthSeconds": 212,
  "thumbnail": "https://...",
  "format": {
    "type": "video",
    "quality": "720p",
    "container": "mp4",
    "url": "https://..."
  },
  "downloadUrl": "https://...",
  "availableFormats": {
    "video": 15,
    "audio": 5
  }
}
```

## Monitoring

### View Function Logs
```bash
doctl serverless activations list
doctl serverless activations get ACTIVATION_ID --logs
```

### Get Function Stats
```bash
doctl serverless activations list --function youtube --limit 10
```

## Updating the Function

After making changes:

```bash
doctl serverless deploy .
```

The function will be updated automatically.

## Cost Estimation

Digital Ocean Functions pricing (as of 2024):
- **Free Tier**: 90,000 GB-seconds per month
- **Beyond Free Tier**: $0.0000185 per GB-second

Example:
- 256 MB function
- 2 second execution
- = 0.512 GB-seconds per request
- Free tier = ~175,000 requests/month

Most personal use cases stay within the free tier!

## Troubleshooting

### "Function not found"
```bash
doctl serverless deploy . --verbose
```

### "Invalid YouTube URL"
Ensure the URL is properly encoded:
```bash
curl "https://YOUR-FUNCTION-URL?url=$(echo 'https://www.youtube.com/watch?v=...' | jq -sRr @uri)"
```

### Timeout Errors
Increase timeout in `project.yml`:
```yaml
limits:
  timeout: 60000  # 60 seconds
```

### Memory Issues
Increase memory in `project.yml`:
```yaml
limits:
  memory: 512  # 512 MB
```

Then redeploy:
```bash
doctl serverless deploy .
```

## Security Notes

- The function has CORS enabled for browser access
- No authentication by default - consider adding API keys for production
- Be mindful of YouTube's Terms of Service
- Consider implementing rate limiting for public deployments

## Next Steps

1. ✅ Deploy the function
2. ✅ Test with cURL
3. ✅ Set up the web UI
4. 🔒 Add authentication (optional)
5. 📊 Set up monitoring
6. 🚀 Share with friends!

## Support

- **Digital Ocean Docs**: https://docs.digitalocean.com/products/functions/
- **ytdl-core Issues**: https://github.com/distubejs/ytdl-core
- **Project Issues**: Open an issue in this repository

Happy downloading! 🎬
