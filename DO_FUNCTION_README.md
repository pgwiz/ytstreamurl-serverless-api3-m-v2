# YouTube Extractor - Digital Ocean Serverless Function

This is a Digital Ocean serverless function for extracting YouTube video information and download URLs. It supports both video and audio-only downloads.

## Features

- ✅ Extract YouTube video information
- 🎵 Audio-only download support
- 🎬 Video with audio download support
- 🎯 Quality selection (highest/lowest)
- 🚀 Fast serverless execution
- 🌐 CORS-enabled API
- 📱 Mobile-friendly web interface

## Project Structure

```
.
├── packages/
│   └── youtube/
│       ├── index.js          # Main function handler
│       └── package.json      # Function dependencies
├── project.yml               # DO Functions configuration
└── youtube-downloader.html   # Web UI
```

## Deployment to Digital Ocean

### Prerequisites

1. Install [doctl](https://docs.digitalocean.com/reference/doctl/how-to/install/) (Digital Ocean CLI)
2. Authenticate with Digital Ocean:
   ```bash
   doctl auth init
   ```

### Deploy

1. Navigate to the project root:
   ```bash
   cd /path/to/ytstreamurl-serverless-api3-m-v2
   ```

2. Deploy the function:
   ```bash
   doctl serverless deploy .
   ```

3. Get the function URL:
   ```bash
   doctl serverless functions list
   ```

4. Test the function:
   ```bash
   curl "https://your-function-url/youtube?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=video"
   ```

## API Usage

### Endpoint

```
GET /youtube
```

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | Yes | - | YouTube video URL |
| `format` | string | No | `video` | Format type: `video` or `audio` |
| `quality` | string | No | `highest` | Quality selection: `highest` or `lowest` |

### Example Request

```bash
curl "https://your-function-url/youtube?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=video&quality=highest"
```

### Example Response

```json
{
  "success": true,
  "videoId": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up",
  "author": "Rick Astley",
  "lengthSeconds": 212,
  "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
  "description": "...",
  "format": {
    "type": "video",
    "quality": "720p",
    "container": "mp4",
    "codec": "avc1.64001F, mp4a.40.2",
    "bitrate": 2000000,
    "url": "https://..."
  },
  "downloadUrl": "https://...",
  "availableFormats": {
    "video": 15,
    "audio": 5
  }
}
```

### Error Response

```json
{
  "error": "Invalid YouTube URL",
  "message": "Please provide a valid YouTube video URL"
}
```

## Web Interface

The `youtube-downloader.html` file provides a user-friendly web interface for the API.

### Setup Web Interface

1. Update the `API_URL` constant in the HTML file with your deployed function URL:
   ```javascript
   const API_URL = 'https://your-function-url/youtube';
   ```

2. Deploy the HTML file to your web hosting or use it locally.

3. Open in a browser and start downloading!

## Local Testing

To test the function locally:

```bash
cd packages/youtube
npm install
npm test
```

This will run a test extraction using the development mode.

## Configuration

The function can be configured in `project.yml`:

- **timeout**: Maximum execution time (default: 30 seconds)
- **memory**: Memory allocation (default: 256 MB)
- **runtime**: Node.js version (default: nodejs:18)

## Differences from simple_proxy.py

This Digital Ocean function is a simplified, focused version of `simple_proxy.py`:

| Feature | simple_proxy.py | DO Function |
|---------|----------------|-------------|
| Platform | Custom Python server | Digital Ocean Functions |
| Runtime | Python + yt-dlp | Node.js + ytdl-core |
| Proxy | Full HTTP/HTTPS proxy | Direct API only |
| Deployment | Manual server setup | Serverless auto-scale |
| Cost | Fixed server cost | Pay-per-use |
| Scaling | Manual | Automatic |

## Troubleshooting

### Function timeout

If you encounter timeout errors, increase the timeout in `project.yml`:

```yaml
limits:
  timeout: 60000  # 60 seconds
```

### Memory issues

If the function runs out of memory:

```yaml
limits:
  memory: 512  # 512 MB
```

### YouTube extraction fails

- Ensure you're using a valid YouTube URL
- Some videos may be region-restricted or age-restricted
- Try a different quality setting

## Security Considerations

- The function includes CORS headers for browser access
- No authentication is implemented by default
- Consider adding rate limiting in production
- Be aware of YouTube's Terms of Service

## License

Same as parent repository

## Support

For issues related to:
- YouTube extraction: Check [@distube/ytdl-core](https://github.com/distubejs/ytdl-core)
- Digital Ocean Functions: Check [DO Functions Documentation](https://docs.digitalocean.com/products/functions/)
