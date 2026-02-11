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

# Note: we rely on yt-dlp being installed via requirements.txt at build time.
# Do not vendor or prepend local vendor dirs; prefer subprocess binary (yt-dlp)
# and fall back to `python -m yt_dlp` when necessary.



# Ensure any vendored packages are on sys.path (installed during build into ./vendor)
import sys
# Search multiple candidate vendor locations (support installs at repo root or package dir)
candidates = [
    os.path.join(os.path.dirname(__file__), 'vendor'),
    os.path.join(os.path.dirname(__file__), '..', 'vendor'),
    os.path.join(os.path.dirname(__file__), '..', '..', 'vendor'),
    os.path.join(os.getcwd(), 'vendor'),
    '/tmp/vendor',  # DigitalOcean remote-build may install --target ./vendor into /tmp
    '/tmp/vendor/lib/python3.11/site-packages',
    '/tmp/.local/lib/python3.11/site-packages',
    '/tmp/.local/lib/python3.11/site-packages/yt_dlp',
]
for v in candidates:
    try:
        v_abs = os.path.abspath(v)
        if os.path.isdir(v_abs):
            sys.path.insert(0, v_abs)
            _log(f'Added vendor dir to sys.path: {v_abs}')
            break
    except Exception as e:
        _log(f'Error checking vendor candidate {v}: {e}')

# We will attempt to import yt_dlp at runtime inside the extractor so that
# imports succeed even if vendor was installed during the build step.

# Check availability of yt-dlp binary in PATH (we can log this early)
try:
    import shutil
    # Primary: check PATH
    YT_DLP_BIN_PATH = shutil.which('yt-dlp')
    if YT_DLP_BIN_PATH:
        _log(f'yt-dlp binary found in PATH at: {YT_DLP_BIN_PATH}')
    else:
        # Common location when the package installs the console script during remote build
        candidate = '/usr/local/bin/yt-dlp'
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            YT_DLP_BIN_PATH = candidate
            _log(f'yt-dlp binary found at common path: {candidate}')
        else:
            _log(f'yt-dlp binary not found in PATH or {candidate}; will attempt `python -m yt_dlp`')
except Exception as e:
    YT_DLP_BIN_PATH = None
    _log(f'Error checking for yt-dlp binary: {e}')


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
        # Attempt to import and use the yt_dlp Python API at runtime (vendor dir already added to sys.path)
        # Ensure runtime vendor candidates are prepended to sys.path right now
        try:
            import sys
            runtime_vendor_paths = ['/tmp/vendor', '/tmp/vendor/lib/python3.11/site-packages', '/tmp/.local/lib/python3.11/site-packages']
            for rp in runtime_vendor_paths:
                try:
                    if os.path.isdir(rp) and rp not in sys.path:
                        sys.path.insert(0, rp)
                        _log(f'Inserted runtime vendor path into sys.path: {rp}')
                except Exception as e:
                    _log(f'Error inserting runtime vendor path {rp}: {e}')
        except Exception:
            pass

        # Module-level variable to surface runtime import errors for diagnostics
        global PY_IMPORT_ERROR
        PY_IMPORT_ERROR = None
        try:
            import yt_dlp as _yt_dlp_module
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
            PY_IMPORT_ERROR = str(api_exc)
            _log(f'yt_dlp Python API failed at runtime: {PY_IMPORT_ERROR}; falling back to subprocess')

        # Subprocess fallback only if binary exists
        if YT_DLP_BIN_PATH or shutil.which(YT_DLP_PATH):
            # Prefer invoking the module with the current Python interpreter so
            # PYTHONPATH/env carrying ensures vendored packages are importable.
            import sys as _sys
            cmd = [_sys.executable, '-m', 'yt_dlp', youtube_url,
                   "--no-cache-dir", "--no-check-certificate", "--dump-single-json",
                   "--no-playlist", "-f", "best[ext=mp4][protocol^=http]/best[protocol^=http]"]
            # If Python import failed earlier, fall back to a vendored binary; otherwise prefer `python -m yt_dlp`
            # Only use vendored binary if the earlier error looks like an import error
            py_err = globals().get('PY_IMPORT_ERROR')
            if py_err and ('No module named' in str(py_err) or 'ImportError' in str(py_err)) and YT_DLP_BIN_PATH:
                # use vendored binary directly
                cmd = [YT_DLP_BIN_PATH, youtube_url, "--no-cache-dir", "--no-check-certificate", "--dump-single-json", "--no-playlist", "-f", "best[ext=mp4][protocol^=http]/best[protocol^=http]"]
                _log('Falling back to vendored binary because of import error')
            else:
                _log('Using subprocess via python -m yt_dlp (preferred)')
            if os.path.exists(COOKIES_FILE):
                cmd.extend(["--cookies", COOKIES_FILE])

            # Prefer binary 'yt-dlp' if present (use subprocess similar to `simple_proxy.py`), otherwise fallback to `python -m yt_dlp`
            if YT_DLP_BIN_PATH:
                cmd = [YT_DLP_BIN_PATH, youtube_url, "--no-cache-dir", "--no-check-certificate", "--dump-single-json", "--no-playlist", "-f", "best[ext=mp4][protocol^=http]/best[protocol^=http]"]
                _log(f'Running binary command: {cmd[0]} ...')
            else:
                import sys as _sys
                cmd = [_sys.executable, '-m', 'yt_dlp', youtube_url, "--no-cache-dir", "--no-check-certificate", "--dump-single-json", "--no-playlist", "-f", "best[ext=mp4][protocol^=http]/best[protocol^=http]"]
                _log(f'Running python module command: {cmd[0]} -m yt_dlp ...')

            if os.path.exists(COOKIES_FILE):
                cmd.extend(["--cookies", COOKIES_FILE])

            env = os.environ.copy()
            existing_pp = env.get('PYTHONPATH', '')
            env['PYTHONPATH'] = existing_pp  # keep as-is; no vendor paths used

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT, env=env)
            except FileNotFoundError as fnf:
                _log(f"yt-dlp executable not found when attempting subprocess: {fnf}")
                return None
            except Exception as e:
                _log(f"yt-dlp subprocess failed: {e}")
                return None

            log_entry['stdout'] = (result.stdout or '')[:2000]
            log_entry['stderr'] = (result.stderr or '')[:2000]
            _log(f"yt-dlp subprocess rc={result.returncode}; stdout_len={len(result.stdout or '')}; stderr_len={len(result.stderr or '')}")

            if result.returncode != 0:
                _log(f"yt-dlp error (code {result.returncode}): {(result.stderr or '')[:800]}")
                return None

            try:
                data = json.loads(result.stdout)
            except Exception as je:
                _log(f'Failed to parse yt-dlp JSON output: {je}');
                return None

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
