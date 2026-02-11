import json
import os
from datetime import datetime

# Minimal handler following DigitalOcean Functions Python runtime guide
# Exposes `main(event, context)` which receives event dict and context object

LOG_DIR = os.environ.get('LOG_DIR', '/tmp/proxyLogs')
os.makedirs(LOG_DIR, exist_ok=True)

def _log(msg):
    ts = datetime.utcnow().isoformat() + 'Z'
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
        with open(os.path.join(LOG_DIR, 'startup.log'), 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

def main(event=None, context=None):
    """Entry point for DigitalOcean Functions (event, context)

    Handles a few simple paths for validation:
      - /health -> returns status
      - /hello -> returns a small JSON message
    """
    _log('main invoked')
    # event may be None for non-http calls
    path = None
    method = 'GET'
    if event and isinstance(event, dict):
        http = event.get('http') or {}
        path = http.get('path')
        method = http.get('method', method)

    # Default behavior: health
    if not path or path == '/health':
        _log('returning health')
        return {"body": {"status": "healthy", "service": "youtube-stream-url"}, "statusCode": 200}

    if path == '/hello':
        _log('returning hello')
        return {"body": {"message": "hello from serverless_handler"}, "statusCode": 200}

    # API: /api/stream/{videoId}
    if path and path.startswith('/api/stream/'):
        video_id = path.split('/')[-1]
        _log(f'api/stream invoked for {video_id}')
        try:
            # Try importing the extractor from the local module
            extract_youtube_stream = None
            # Try direct import first
            try:
                from serverless_handler_local import extract_youtube_stream as _ext
                extract_youtube_stream = _ext
            except Exception:
                # Fallback: load by file path using importlib
                try:
                    import importlib.util
                    base = os.path.dirname(__file__)
                    cwd = os.getcwd()
                    candidates = [
                        os.path.join(base, '..', 'serverless_handler_local.py'),
                        os.path.join(base, '..', '..', 'serverless_handler_local.py'),
                        os.path.join(cwd, 'serverless_handler_local.py'),
                        os.path.join(cwd, 'packages', 'default', 'serverless_handler_local.py'),
                        os.path.join(cwd, 'packages', 'default', 'serverless_handler', 'serverless_handler_local.py'),
                        os.path.join(base, 'serverless_handler_local.py')
                    ]
                    found = None
                    for p in candidates:
                        p_abs = os.path.abspath(p)
                        if os.path.exists(p_abs):
                            found = p_abs
                            break
                    if not found:
                        # Fallback: define extractor inline so the function can run even if the
                        # helper module was not packaged correctly.
                        _log('serverless_handler_local.py not found; using inline extractor')
                        def extract_youtube_stream(video_id):
                            try:
                                youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                                cmd = [
                                    os.environ.get('YT_DLP_PATH', 'yt-dlp'),
                                    youtube_url,
                                    "--no-cache-dir",
                                    "--no-check-certificate",
                                    "--dump-single-json",
                                    "--no-playlist",
                                    "-f",
                                    "best[ext=mp4][protocol^=http]/best[protocol^=http]",
                                ]
                                cookies = os.environ.get('COOKIES_FILE', '/tmp/cookies.txt')
                                if os.path.exists(cookies):
                                    cmd.extend(["--cookies", cookies])
                                _log(f"Running (inline): {' '.join(cmd)}")
                                result = subprocess.run(cmd, capture_output=True, text=True, timeout=int(os.environ.get('REQUEST_TIMEOUT', '45')))
                                if result.returncode != 0:
                                    _log(f"yt-dlp error (code {result.returncode}): {result.stderr[:200]}")
                                    return None
                                data = json.loads(result.stdout)
                                stream_url = data.get('url')
                                if not stream_url:
                                    _log('No URL found in yt-dlp output (inline)')
                                    return None
                                return {
                                    'title': data.get('title', 'Unknown'),
                                    'url': stream_url,
                                    'thumbnail': data.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"),
                                    'duration': str(data.get('duration', 0)),
                                    'uploader': data.get('uploader', 'Unknown'),
                                    'id': video_id,
                                    'videoId': video_id,
                                    'format_id': data.get('format_id'),
                                    'ext': data.get('ext', 'mp4')
                                }
                            except Exception as e:
                                _log(f'Inline extraction error: {e}')
                                return None
                    else:
                        spec = importlib.util.spec_from_file_location('sh_local', found)
                        shl = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(shl)
                        extract_youtube_stream = shl.extract_youtube_stream
                except Exception as e:
                    _log(f'Import error: {e}')
                    raise

            result = extract_youtube_stream(video_id)
            if result:
                return {"body": result, "statusCode": 200}
            else:
                return {"body": {"error": "Failed to extract stream"}, "statusCode": 500}
        except Exception as e:
            _log(f'extraction error: {e}')
            return {"body": {"error": str(e)}, "statusCode": 500}

    # Direct ytdlp endpoint: /ytdlp?id={videoId}
    if path == '/ytdlp':
        q = event.get('query', {}) if event else {}
        vid = q.get('id') if isinstance(q, dict) else None
        if not vid:
            return {"body": {"error": "Missing 'id' parameter"}, "statusCode": 400}
        try:
            from serverless_handler_local import extract_youtube_stream
            result = extract_youtube_stream(vid)
            if result:
                return {"body": result, "statusCode": 200}
            return {"body": {"error": "Failed to extract stream"}, "statusCode": 500}
        except Exception as e:
            _log(f'ytdlp error: {e}')
            return {"body": {"error": str(e)}, "statusCode": 500}

    # Unknown path
    _log(f'unknown path: {path}')
    return {"body": {"error": "Not found", "path": path}, "statusCode": 404}
