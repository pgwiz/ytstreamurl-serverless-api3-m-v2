import json
import os
import subprocess
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

    # Serve playground UI and static assets
    if path == '/playground':
        try:
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            p = os.path.join(static_dir, 'playground.html')
            with open(p, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"body": content, "statusCode": 200, "headers": {"Content-Type": "text/html; charset=utf-8"}}
        except Exception as e:
            _log(f'playground serve error: {e}')
            return {"body": {"error": "Could not serve playground"}, "statusCode": 500}

    if path and ('/static/' in path):
        try:
            # Normalize: find the first occurrence of /static/ to support prefixes like
            # /default/serverless_handler/static/playground.js
            idx = path.find('/static/')
            rel = path[idx + len('/static/'):]
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            # Prevent path traversal
            target = os.path.abspath(os.path.join(static_dir, rel))
            if not target.startswith(os.path.abspath(static_dir)) or not os.path.exists(target):
                return {"body": {"error": "Not found"}, "statusCode": 404}
            import mimetypes
            mime, _ = mimetypes.guess_type(target)
            mime = mime or 'application/octet-stream'
            mode = 'rb' if not mime.startswith('text/') else 'r'
            with open(target, mode, encoding='utf-8' if mode=='r' else None) as f:
                data = f.read()
            headers = {"Content-Type": mime}
            return {"body": data, "statusCode": 200, "headers": headers}
        except Exception as e:
            _log(f'static serve error: {e}')
            return {"body": {"error": "Not found"}, "statusCode": 404}

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
                # Diagnostic step: attempt a CLI run with verbose output to capture errors
                try:
                    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                    diag_cmd = [
                        os.environ.get('YT_DLP_PATH', 'yt-dlp'),
                        youtube_url,
                        "--no-cache-dir",
                        "--no-check-certificate",
                        "--dump-single-json",
                        "--no-playlist",
                        "-f",
                        "best[ext=mp4]/best",
                        "-v"
                    ]
                    _log(f"Running diagnostic command: {' '.join(diag_cmd)}")
                    proc = subprocess.run(diag_cmd, capture_output=True, text=True, timeout=int(os.environ.get('REQUEST_TIMEOUT', '45')))
                    stderr = proc.stderr or ''
                    stdout = proc.stdout or ''
                    _log(f"Diagnostic rc={proc.returncode} stderr={(stderr[:300]).replace(chr(10),' ')}")
                    # Include any Python import error in the diagnostic if present
                    py_import_err = None
                    try:
                        from serverless_handler_local import __dict__ as _m
                        py_import_err = _m.get('py_exc')
                    except Exception:
                        py_import_err = None
                    diagnostic = {"rc": proc.returncode, "stderr": stderr[:2000], "stdout_sample": stdout[:2000]}
                    if py_import_err:
                        diagnostic['python_import_error'] = py_import_err
                    return {"body": {"error": "Failed to extract stream", "diagnostic": diagnostic}, "statusCode": 500}
                except Exception as de:
                    _log(f'Diagnostic run failed: {de}')
                    return {"body": {"error": "Failed to extract stream", "diagnostic_error": str(de)}, "statusCode": 500}
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
    # API: /api/search/youtube
    if path and path.startswith('/api/search/youtube'):
        q = event.get('query', {}) if event else {}
        query = (q.get('query') or q.get('q')) if isinstance(q, dict) else None
        try:
            limit = int(q.get('limit', 5)) if isinstance(q.get('limit', None), (str, int)) else 5
        except Exception:
            limit = 5
        if not query:
            return {"body": {"error": "Missing 'query' parameter"}, "statusCode": 400}
        _log(f'api/search/youtube invoked for query="{query}" limit={limit}')
        try:
            # Prefer helper from serverless_handler_local if available
            try:
                from serverless_handler_local import search_youtube as _search
            except Exception:
                _log('serverless_handler_local.search_youtube not available; using inline search')
                def _search(query, limit=5):
                    try:
                        import yt_dlp
                        ydl_opts = {'quiet': True, 'skip_download': True, 'nocheckcertificate': True}
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            data = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
                        entries = data.get('entries', []) if isinstance(data, dict) else []
                        results = []
                        for e in entries:
                            results.append({
                                'id': e.get('id'),
                                'title': e.get('title'),
                                'duration': str(e.get('duration', 0)) if e.get('duration') is not None else '0',
                                'url': f"https://www.youtube.com/watch?v={e.get('id')}",
                                'thumbnail': e.get('thumbnail')
                            })
                        return results
                    except Exception as e:
                        _log(f'Inline search error: {e}')
                        return []
            results = _search(query, limit)
            return {"body": {"query": query, "limit": limit, "results": results}, "statusCode": 200}
        except Exception as e:
            _log(f'search error: {e}')
            return {"body": {"error": str(e)}, "statusCode": 500}
    # Unknown path
    _log(f'unknown path: {path}')
    return {"body": {"error": "Not found", "path": path}, "statusCode": 404}
