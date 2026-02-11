import json
import subprocess
import os
from datetime import datetime

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


# Check availability of yt_dlp Python API at import time to provide clearer diagnostics
try:
    import yt_dlp as _yt_dlp_module
    YT_DLP_PY_AVAILABLE = True
    _log('yt_dlp Python module is available')
except Exception as e:
    YT_DLP_PY_AVAILABLE = False
    _log(f'yt_dlp Python module NOT available: {e}')

# Check availability of yt-dlp binary in PATH
try:
    import shutil
    YT_DLP_BIN_PATH = shutil.which(YT_DLP_PATH)
    if YT_DLP_BIN_PATH:
        _log(f'yt-dlp binary found at: {YT_DLP_BIN_PATH}')
    else:
        _log(f'yt-dlp binary not found for YT_DLP_PATH="{YT_DLP_PATH}"')
except Exception:
    YT_DLP_BIN_PATH = None
    _log('Error checking for yt-dlp binary')


def extract_youtube_stream(video_id):
    log_entry = {
        "video_id": video_id,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "stdout": "",
        "stderr": "",
        "success": False
    }

    try:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        # Prefer using the yt_dlp Python API when available (no external binary dependency)
        # Prefer Python API when available
        if YT_DLP_PY_AVAILABLE:
            try:
                _log('Using yt_dlp Python API')
                ydl_opts = {
                    'format': 'best[ext=mp4][protocol^=http]/best[protocol^=http]',
                    'skip_download': True,
                    'quiet': True,
                    'nocheckcertificate': True,
                    'noplaylist': True,
                }
                if os.path.exists(COOKIES_FILE):
                    ydl_opts['cookiefile'] = COOKIES_FILE
                with _yt_dlp_module.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(youtube_url, download=False)
                data = info
                stream_url = data.get('url') or (data.get('formats')[-1].get('url') if data.get('formats') else None)
                if not stream_url:
                    _log('No URL found in yt_dlp API output')
                    return None
            except Exception as api_exc:
                _log(f'yt_dlp Python API failed at runtime: {api_exc}; falling back to subprocess')
        else:
            _log('yt_dlp Python API not available; attempting subprocess fallback')

        # Subprocess fallback only if binary exists
        if YT_DLP_BIN_PATH or shutil.which(YT_DLP_PATH):
            cmd = [
                YT_DLP_BIN_PATH or YT_DLP_PATH,
                youtube_url,
                "--no-cache-dir",
                "--no-check-certificate",
                "--dump-single-json",
                "--no-playlist",
                "-f",
                "best[ext=mp4][protocol^=http]/best[protocol^=http]",
            ]
            if os.path.exists(COOKIES_FILE):
                cmd.extend(["--cookies", COOKIES_FILE])

            _log(f"Running: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT)
            except FileNotFoundError as fnf:
                _log(f"yt-dlp binary not found when attempting subprocess: {fnf}")
                return None

            log_entry['stdout'] = result.stdout[:1000]
            log_entry['stderr'] = result.stderr[:1000]

            if result.returncode != 0:
                _log(f"yt-dlp error (code {result.returncode}): {result.stderr[:200]}")
                return None

            data = json.loads(result.stdout)
            stream_url = data.get('url')
            if not stream_url:
                _log('No URL found in yt-dlp output')
                return None
        else:
            _log('No yt_dlp Python module and no yt-dlp binary available; cannot extract')
            return None

        log_entry['success'] = True
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
        _log('yt-dlp timeout')
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
