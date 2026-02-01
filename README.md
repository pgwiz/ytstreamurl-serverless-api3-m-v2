# YouTube Stream URL API (Node.js)

A serverless API to stream YouTube videos, search YouTube/Spotify, and extract playlist data.
Now fully converted to Node.js (removing Python dependency).

**Codeowner:** pgwiz

---

## 🚀 Features

- **Streaming:** High-quality audio stream URL extraction.
- **Mixes/Radio:** Full support for YouTube Mixes (`?limit=X`).
- **Searching:** YouTube and Spotify search endpoints.
- **Playlists:** Extract metadata from YouTube and Spotify playlists.
- **Playground:** Interactive GUI for testing (`/playground`).

---

## 🛠️ Usage

### Prerequisites
- Node.js v18+
- Spotify Client ID & Secret (for Spotify features)
- `PLAYGROUND=true` (to enable developer GUI)

### Installation
```bash
npm install
```

### Local Development
```bash
# Start server on port 3000
npm run dev
```

### Environment Variables
Create a `.env` file or set in Vercel:

| Variable | Description |
|----------|-------------|
| `PORT` | Server port (default: 3000) |
| `SPOTIFY_CLIENT_ID` | Your Spotify Client ID |
| `SPOTIFY_CLIENT_SECRET` | Your Spotify Client Secret |
| `PLAYGROUND` | Set to `true` to enable `/playground` |
| `COOKIES` | Netscape format cookies (string) or JSON array (optional) |
| `PROXY` | HTTP Proxy URL (e.g., `http://user:pass@host:port`) for Vercel IP Bypass |

---

## 📚 API Endpoints

### 1. Developer Playground
- **URL:** `/playground`
- **Method:** `GET`
- **Note:** Requires `PLAYGROUND=true`

### 2. Stream Extraction
- **URL:** `/get`
- **Method:** `GET`
- **Params:** 
  - `ytl` (required): YouTube Video, Playlist, or Mix URL
  - `limit` (optional): Max results (default: 5)

### 3. YouTube Search
- **URL:** `/api/search/youtube`
- **Params:** `query`, `limit`

### 4. Spotify Search
- **URL:** `/api/search/spotify`
- **Params:** `query`, `type`, `limit`

---

## 📦 Deployment

### Vercel

```bash
vercel --prod
```

### Digital Ocean Functions

For a lightweight YouTube-only downloader, see the **Digital Ocean Serverless Function** version:

- **Location:** `packages/youtube/`
- **Documentation:** [DO_FUNCTION_README.md](DO_FUNCTION_README.md)
- **UI:** [youtube-downloader.html](youtube-downloader.html)

Deploy to Digital Ocean:
```bash
doctl serverless deploy .
```

This serverless function provides:
- ✅ YouTube video extraction (audio & video)
- 🎯 Quality selection
- 🚀 Auto-scaling serverless architecture
- 📱 Mobile-friendly web interface

---

**Version:** v3.5.0
