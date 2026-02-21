import json
import subprocess
import os
from datetime import datetime

# Version marker for deployment verification
__VERSION__ = "2026.02.17.001"

# Check for cookies.txt in package directory first, then fall back to env var
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_COOKIES = os.path.join(_PACKAGE_DIR, 'cookies.txt')
if os.path.exists(_LOCAL_COOKIES):
    COOKIES_FILE = _LOCAL_COOKIES
else:
    COOKIES_FILE = os.environ.get('COOKIES_FILE', '/tmp/cookies.txt')

YT_DLP_PATH = os.environ.get('YT_DLP_PATH', 'yt-dlp')
LOG_DIR = os.environ.get('LOG_DIR', '/tmp/proxyLogs')
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '45'))

os.makedirs(LOG_DIR, exist_ok=True)


def _log(msg):
    ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass

# Note: we rely on yt-dlp being installed via requirements.txt at build time.
# Do not vendor or prepend local vendor dirs; prefer subprocess binary (yt-dlp)
# and fall back to `python -m yt_dlp` when necessary.



# We rely on yt-dlp being installed via requirements.txt at build time.
import sys
import shutil

# yt-dlp will be available via pip install in requirements.txt





def extract_youtube_stream_nodejs(video_id):
    """Extract YouTube stream using Node.js ytdl-core as subprocess.

    This is called when yt-dlp signature solving fails and uses Node.js runtime
    for JavaScript execution (which is available in some serverless environments).

    Returns dict with stream info or None on failure.
    """
    try:
        import shutil as _shutil
        import sys as _sys

        # Find Node.js executable
        node_path = _shutil.which('node')
        if not node_path:
            _log('⚠️  Node.js not found in PATH')
            return None

        # Find the extract_youtube_nodejs.js script
        script_candidates = [
            os.path.join(os.path.dirname(__file__), 'extract_youtube_nodejs.js'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'extract_youtube_nodejs.js'),
            os.path.join(os.getcwd(), 'extract_youtube_nodejs.js'),
        ]

        script_path = None
        for candidate in script_candidates:
            if os.path.exists(candidate):
                script_path = os.path.abspath(candidate)
                break

        if not script_path:
            _log('⚠️  extract_youtube_nodejs.js not found')
            return None

        _log(f'🟢 Using Node.js for signature solving: {node_path}')

        # Build command
        cmd = [node_path, script_path, video_id]

        # Add cookies if available
        if os.path.exists(COOKIES_FILE):
            cmd.append(COOKIES_FILE)
            _log(f'🍪 Node.js using cookies: {COOKIES_FILE}')

        try:
            _log(f'Running Node.js extraction...')
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if 'error' in data:
                        _log(f'Node.js error: {data.get("reason", data.get("error"))}')
                        return None

                    stream_url = data.get('url')
                    if stream_url:
                        _log(f'✅ Node.js extraction succeeded')
                        return {
                            'title': data.get('title', 'Unknown'),
                            'url': stream_url,
                            'thumbnail': data.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"),
                            'duration': str(data.get('duration', 0)),
                            'uploader': data.get('uploader', 'Unknown'),
                            'id': video_id,
                            'videoId': video_id,
                            'format_id': data.get('format_id'),
                            'ext': data.get('ext', 'mp4'),
                            'resolution': data.get('resolution', 'unknown')
                        }
                except json.JSONDecodeError as je:
                    _log(f'Node.js JSON error: {je}')
                    return None
            else:
                stderr = (result.stderr or '')[:200]
                _log(f'Node.js failed (rc={result.returncode}): {stderr}')
                return None

        except subprocess.TimeoutExpired:
            _log('Node.js extraction timed out')
            return None
        except Exception as e:
            _log(f'Node.js subprocess error: {e}')
            return None

    except Exception as e:
        _log(f'Node.js extraction setup error: {e}')
        return None


def extract_youtube_stream(video_id):
    """Extract YouTube stream using yt-dlp (simple proven logic)."""
    try:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Build yt-dlp command
        cmd = [
            'yt-dlp',
            youtube_url,
            "--no-cache-dir",
            "--no-check-certificate",
            "--dump-single-json",
            "--no-playlist",
            "-f", "best[ext=mp4][protocol^=http]/best[protocol^=http]"
        ]
        
        # Add Node.js as JS runtime if available
        node_path = shutil.which('node')
        if node_path:
            cmd.extend(['--js-runtimes', f'node:{node_path}'])
            _log(f'Using Node.js JS runtime: {node_path}')
        else:
            _log('⚠️  Node.js not available - signature solving may fail')
        
        # Add cookies if file exists
        if os.path.exists(COOKIES_FILE):
            cmd.extend(["--cookies", COOKIES_FILE])
        
        _log(f'Extracting {video_id}...')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT)
        
        if result.returncode != 0:
            _log(f'yt-dlp error (rc={result.returncode}): {result.stderr[:200]}')
            return None
        
        data = json.loads(result.stdout)
        stream_url = data.get('url')
        
        if not stream_url:
            _log(f'No URL in yt-dlp output for {video_id}')
            return None
        
        _log(f'✅ Extracted {video_id}')
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
    except subprocess.TimeoutExpired:
        _log(f'Timeout extracting {video_id}')
        return None
    except Exception as e:
        _log(f'Extraction error: {e}')
        return None


def search_youtube(query, limit=5):
    """Search YouTube using yt_dlp's ytsearch and return simple result objects."""
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
        _log(f'search_youtube error: {e}')
        return []
