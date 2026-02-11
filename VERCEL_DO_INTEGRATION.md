# DigitalOcean Serverless Integration (Vercel)

## Overview
The Vercel deployment (`api/index.js`) can now use your DigitalOcean serverless function as the primary source for YouTube stream extraction. This allows you to leverage the cloud backend while maintaining Vercel as your front-end API gateway.

## Setup

### 1. Deploy DigitalOcean Serverless Function
First, ensure your DigitalOcean function is deployed:
```bash
doctl serverless deploy . --include default --remote-build
```

Get your function URL:
```bash
doctl serverless functions get serverless_handler --url
```

This will return something like:
```
https://faas-fra1-afec6ce7.doserverless.co/api/v1/web/fn-bb05ab8d-3ad1-453e-a3ef-da38e7e0d078/default/serverless_handler
```

### 2. Set DIGITALOCEAN_URL in Vercel

In your Vercel project settings, add the environment variable:

**Variable Name:** `DIGITALOCEAN_URL`  
**Value:** `https://faas-fra1-afec6ce7.doserverless.co/api/v1/web/fn-bb05ab8d-3ad1-453e-a3ef-da38e7e0d078/default/serverless_handler`

Or using Vercel CLI:
```bash
vercel env add DIGITALOCEAN_URL
# Paste your function URL when prompted
```

### 3. Redeploy Vercel

```bash
vercel deploy --prod
```

Or use git push if you have GitHub integration enabled.

## How It Works

When you call `/stream/{videoId}` on Vercel:

1. **Check DIGITALOCEAN_URL**: If the env var is set, Vercel fetches from the DigitalOcean function at `{DIGITALOCEAN_URL}/api/stream/{videoId}`
2. **Response Processing**: The DigitalOcean function returns a full response with:
   - `url`: Full HTTPS streaming URL (from Google CDN, already valid, no stripping needed)
   - `title`, `uploader`, `thumbnail`, `duration`, etc.
3. **Fallback**: If DO fetch fails or times out, Vercel falls back to local `ytdl` extraction
4. **Return**: Response is passed back to client as-is (no URL modification)

### Response Example
```json
{
  "videoId": "dQw4w9WgXcQ",
  "streamUrl": "https://rr3---sn-4g5ednsl.googlevideo.com/videoplayback?...",
  "url": "https://rr3---sn-4g5ednsl.googlevideo.com/videoplayback?...",
  "title": "Rick Astley - Never Gonna Give You Up",
  "uploader": "Rick Astley",
  "duration": "213",
  "thumbnail": "https://i.ytimg.com/vi_webp/dQw4w9WgXcQ/maxresdefault.webp",
  "ext": "mp4",
  "format_id": "18"
}
```

## Environment Variables Summary

| Variable | Source | Purpose |
|----------|--------|---------|
| `SPOTIFY_CLIENT_ID` | Vercel secrets | Spotify API auth |
| `SPOTIFY_CLIENT_SECRET` | Vercel secrets | Spotify API auth |
| `PROXY` | Vercel env (optional) | Legacy proxy URL (overridden by DIGITALOCEAN_URL for /stream) |
| `DIGITALOCEAN_URL` | Vercel env | DigitalOcean serverless function base URL |

## Benefits

✅ **Scalability**: DigitalOcean handles heavy extraction workloads  
✅ **Reliability**: Falls back to Vercel if DO is down  
✅ **Cost**: Distribute load between Vercel (API gateway) and DO (extraction)  
✅ **Simple**: No URL manipulation needed (DO returns valid HTTPS URLs directly)  

## Troubleshooting

### Getting 500 error from /stream

Check Vercel logs:
```bash
vercel logs
```

Common issues:
- **DIGITALOCEAN_URL not set**: Function will use local extraction
- **DO function offline**: Falls back to local extraction automatically
- **Wrong URL format**: Ensure DIGITALOCEAN_URL is exactly the function base URL

### Testing

Test the integration locally:
```bash
export DIGITALOCEAN_URL="https://your-do-function-url"
node api/index.js
# Then curl http://localhost:3000/stream/dQw4w9WgXcQ
```
