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
        cmd = [
            YT_DLP_PATH,
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT)
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
