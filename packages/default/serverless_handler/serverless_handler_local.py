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



# We do not rely on vendored directories. Behavior:
# - Prefer running the `yt-dlp` subprocess binary (installed by pip during remote build).
# - If no binary is found, attempt `python -m yt_dlp` as a subprocess.
import sys

# We will attempt to import yt_dlp at runtime inside the extractor so that
# imports succeed even if vendor was installed during the build step.

# Check availability of yt-dlp binary in PATH (we can log this early)
try:
            import shutil, sys
            # Check PATH first
            YT_DLP_BIN_PATH = shutil.which('yt-dlp')
            if YT_DLP_BIN_PATH:
                _log(f'yt-dlp binary found in PATH at: {YT_DLP_BIN_PATH}')
            else:
                # Check common locations where pip might have installed the console script
                candidates = [
                    '/usr/local/bin/yt-dlp',
                    '/root/.local/bin/yt-dlp',
                    '/home/function/.local/bin/yt-dlp',
                    '/tmp/.local/bin/yt-dlp',
                    '/usr/bin/yt-dlp'
                ]
                # Add Python's scripts directory (Windows or virtualenv)
                try:
                    scripts_dir = os.path.join(os.path.dirname(sys.executable), 'Scripts')
                    candidates.append(os.path.join(scripts_dir, 'yt-dlp.exe'))
                    # Add user scripts dir on Windows
                    user_scripts = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', f'Python{sys.version_info.major}{sys.version_info.minor}', 'Scripts', 'yt-dlp.exe')
                    candidates.append(user_scripts)
                except Exception:
                    pass

            try:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    found = candidate
                    break
            except Exception:
                continue
        if found:
            YT_DLP_BIN_PATH = found
            _log(f'yt-dlp binary found at common path: {found}')
        else:
            YT_DLP_BIN_PATH = None
            _log('yt-dlp binary not found in PATH or common locations; will attempt `python -m yt_dlp` subprocess')
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

        # Try subprocess first (preferred): use binary if available, otherwise `python -m yt_dlp`.
        cmd = None
        if YT_DLP_BIN_PATH:
            cmd = [YT_DLP_BIN_PATH, youtube_url, "--no-cache-dir", "--no-check-certificate", "--dump-single-json", "--no-playlist", "-f", "best[ext=mp4][protocol^=http]/best[protocol^=http]"]
            _log(f'Using yt-dlp binary for extraction: {YT_DLP_BIN_PATH}')
        else:
            # Prefer python -m yt_dlp so PYTHONPATH and installed package is used
            import sys as _sys
            cmd = [_sys.executable, '-m', 'yt_dlp', youtube_url, "--no-cache-dir", "--no-check-certificate", "--dump-single-json", "--no-playlist", "-f", "best[ext=mp4][protocol^=http]/best[protocol^=http]"]
            _log(f'Using python -m yt_dlp subprocess: {_sys.executable} -m yt_dlp')

        if os.path.exists(COOKIES_FILE):
            cmd.extend(["--cookies", COOKIES_FILE])

        try:
            _log(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT)
        except FileNotFoundError as fnf:
            _log(f"yt-dlp not found when attempting subprocess: {fnf}")
            return None
        except Exception as e:
            _log(f"yt-dlp subprocess failed: {e}")
            return None

        if result.returncode != 0:
            _log(f"yt-dlp error (code {result.returncode}): {(result.stderr or '')[:400]}")
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
