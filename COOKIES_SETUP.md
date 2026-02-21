# Cookies Setup for YouTube Authentication

## Why Use Cookies?

Some YouTube videos require authentication/login to access:
- Age-restricted content
- Region-locked videos  
- Member-only content
- Videos that require "Sign in to confirm you're not a bot"

## How to Get YouTube Cookies (Netscape Format)

### Method 1: Browser Extension (Recommended)

1. **Install Extension:**
   - Chrome: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. **Export Cookies:**
   - Go to `youtube.com` and log in
   - Click the extension icon
   - Click "Export" or "Download"
   - Save as `cookies.txt`

### Method 2: Using yt-dlp (if installed locally)

```bash
# Extract cookies from your browser
yt-dlp --cookies-from-browser chrome --cookies cookies.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

## Deploy Cookies to DigitalOcean Functions

### Option 1: Environment Variable (if cookies are small)

```bash
# Not recommended for large cookie files
doctl serverless functions invoke serverless_handler --param COOKIES_FILE=/tmp/cookies.txt
```

### Option 2: Upload During Build

1. Place `cookies.txt` in your project root
2. Update `packages/default/serverless_handler/build.sh`:

```bash
#!/bin/bash
# Copy cookies during build
cp ../../../cookies.txt /tmp/cookies.txt 2>/dev/null || true
```

3. Deploy:
```bash
doctl serverless deploy . --include default --remote-build
```

### Option 3: Mount as Secret/Volume (Advanced)

Check DigitalOcean Functions documentation for mounting secrets.

## Verify Cookies Setup

After deployment, check if cookies are detected:

```bash
curl https://YOUR_FUNCTION_URL/debug/cookies
```

Expected response when cookies are present:
```json
{
  "path": "/tmp/cookies.txt",
  "exists": true,
  "size": 1234,
  "readable": true,
  "line_count": 25,
  "netscape_format": true,
  "first_line": "# Netscape HTTP Cookie File"
}
```

## Test with Age-Restricted Video

```bash
# Before cookies (should fail with LOGIN_REQUIRED):
curl "https://YOUR_FUNCTION_URL/api/stream/kffacxfA7G4"

# After cookies (should succeed):
curl "https://YOUR_FUNCTION_URL/api/stream/kffacxfA7G4"
```

## Security Notes

⚠️ **Important:**
- Never commit `cookies.txt` to git (already in `.gitignore`)
- Cookies contain your YouTube session - treat like a password
- Cookies expire - you may need to refresh them periodically
- Use cookies only on trusted servers

## Troubleshooting

### Cookies not working?

1. Check format:
   ```bash
   head -1 cookies.txt
   # Should output: # Netscape HTTP Cookie File
   ```

2. Check permissions:
   ```bash
   ls -la /tmp/cookies.txt
   # Should be readable
   ```

3. Check logs - you should see:
   ```
   ✅ Using cookies file: /tmp/cookies.txt
   🍪 Cookies will be sent to bypass age/region restrictions
   ```

4. If using browser extension, make sure to export in **Netscape format** (not JSON)

## Cookie File Format

Netscape format is tab-separated with 7 fields:
```
domain	flag	path	secure	expiration	name	value
```

Example:
```
.youtube.com	TRUE	/	TRUE	1735689600	CONSENT	YES+cb.20210101-00-p0
.youtube.com	TRUE	/	FALSE	1735689600	PREF	f1=50000000
```

## See Also

- [yt-dlp cookies documentation](https://github.com/yt-dlp/yt-dlp#authenticated-downloads)
- [cookies.example.txt](./cookies.example.txt) - Template file
