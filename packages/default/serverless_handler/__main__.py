import json
import os
import subprocess
from datetime import datetime

# Minimal handler following DigitalOcean Functions Python runtime guide
# Exposes `main(event, context)` which receives event dict and context object

LOG_DIR = os.environ.get('LOG_DIR', '/tmp/proxyLogs')
os.makedirs(LOG_DIR, exist_ok=True)
import sys

def _log(msg):
    ts = datetime.utcnow().isoformat() + 'Z'
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
        with open(os.path.join(LOG_DIR, 'startup.log'), 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

# Do not add vendor dirs to sys.path; rely on packages installed from requirements
# and prefer subprocess 'yt-dlp' for stream extraction as in `simple_proxy.py`.

# Keep a minimal check for /tmp/vendor presence for backward compatibility
vendor_candidates = [
    '/tmp/vendor',
    os.path.join(os.path.dirname(__file__), 'vendor')
]
for vc in vendor_candidates:
    try:
        vc_abs = os.path.abspath(vc)
        _log(f'Checked vendor candidate: {vc_abs} exists={os.path.isdir(vc_abs)}')
    except Exception as e:
        _log(f'Error checking vendor candidate {vc}: {e}')

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

    # Debug endpoint to inspect Python sys.path and vendor locations
    if path and ('/debug/sys' in path):
        try:
            import sys
            import shutil
            vendors = [
                os.path.join(os.path.dirname(__file__), 'vendor'),
                os.path.join(os.path.dirname(__file__), '..', 'vendor'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'vendor'),
                os.path.join(os.getcwd(), 'vendor'),
            ]
            vendor_info = {}
            for v in vendors:
                try:
                    v_abs = os.path.abspath(v)
                    vendor_info[v_abs] = os.path.isdir(v_abs)
                except Exception as e:
                    vendor_info[v] = f'error: {e}'
            python_check = {
                'sys_path': sys.path[:20],
                'yt_dlp_importable': None,
                'yt_dlp_location': None,
                'yt_dlp_bin': shutil.which(os.environ.get('YT_DLP_PATH', 'yt-dlp')),
                'site_packages_candidates': []
            }
            # Check common site-packages locations under /tmp that pip might have used
            sp_candidates = [
                '/tmp/vendor',
                '/tmp/vendor/lib',
                '/tmp/vendor/lib/python3.11/site-packages',
                '/tmp/.local/lib/python3.11/site-packages',
                '/tmp/.local/lib/python3.11/site-packages/yt_dlp',
            ]
            for sc in sp_candidates:
                try:
                    python_check['site_packages_candidates'].append({sc: os.path.isdir(sc)})
                except Exception as e:
                    python_check['site_packages_candidates'].append({sc: f'error: {e}'})

            # Try import and also enumerate vendor directories if present
            try:
                import yt_dlp as _ym
                python_check['yt_dlp_importable'] = True
                python_check['yt_dlp_location'] = getattr(_ym, '__file__', None)
            except Exception as ie:
                python_check['yt_dlp_importable'] = False
                python_check['yt_dlp_import_error'] = str(ie)
                # Enumerate vendor dirs to help debugging
                vendor_listing = {}
                for k, present in vendor_info.items():
                    try:
                        if present:
                            vendor_listing[k] = os.listdir(k)
                        else:
                            vendor_listing[k] = 'not present'
                    except Exception as e:
                        vendor_listing[k] = f'error listing: {e}'
                python_check['vendor_listing_sample'] = vendor_listing

            # Attempt to run the module directly to get its version (falls back to non-binary)
            try:
                import sys as _sys
                proc_ver = subprocess.run([_sys.executable, '-m', 'yt_dlp', '--version'], capture_output=True, text=True, timeout=5)
                python_check['yt_dlp_module_version'] = (proc_ver.stdout or '').strip()
                python_check['yt_dlp_module_version_rc'] = proc_ver.returncode
            except Exception as ver_e:
                python_check['yt_dlp_module_version_error'] = str(ver_e)

            return {"body": {"vendor_candidates": vendor_info, "python_check": python_check}, "statusCode": 200}
        except Exception as e:
            _log(f'debug error: {e}')
            return {"body": {"error": str(e)}, "statusCode": 500}

    # Lightweight python import check endpoint: /debug/py
    if path and ('/debug/py' in path):
        try:
            try:
                import yt_dlp as _ym
                return {"body": {"yt_dlp": True, "location": getattr(_ym, '__file__', None)}, "statusCode": 200}
            except Exception as ie:
                return {"body": {"yt_dlp": False, "error": str(ie)}, "statusCode": 200}
        except Exception as e:
            _log(f'debug/py error: {e}')
            return {"body": {"error": str(e)}, "statusCode": 500}

    # Debug endpoint to check `python -m yt_dlp --version`
    if path and ('/debug/ytdlp_version' in path):
        try:
            import sys as _sys
            env = os.environ.copy()
            existing_pp = env.get('PYTHONPATH', '')
            vendor_paths = []
            for p in ['/tmp/vendor', '/tmp/vendor/lib/python3.11/site-packages', '/tmp/.local/lib/python3.11/site-packages']:
                try:
                    if os.path.isdir(p):
                        vendor_paths.append(p)
                except Exception:
                    continue
            new_pp = os.pathsep.join(vendor_paths) if vendor_paths else ''
            if new_pp and existing_pp:
                env['PYTHONPATH'] = new_pp + os.pathsep + existing_pp
            elif new_pp:
                env['PYTHONPATH'] = new_pp
            else:
                env['PYTHONPATH'] = existing_pp

            proc = subprocess.run([_sys.executable, '-m', 'yt_dlp', '--version'], capture_output=True, text=True, timeout=5, env=env)
            return {"body": {"version": (proc.stdout or '').strip(), "rc": proc.returncode, "stderr": (proc.stderr or '').strip()}, "statusCode": 200}
        except Exception as e:
            _log(f'debug/ytdlp_version error: {e}')
            return {"body": {"error": str(e)}, "statusCode": 500}

    # Debug endpoint to check cookies file status
    if path and ('/debug/cookies' in path):
        try:
            # Check local package directory first
            _package_dir = os.path.dirname(os.path.abspath(__file__))
            _local_cookies = os.path.join(_package_dir, 'cookies.txt')
            
            if os.path.exists(_local_cookies):
                cookies_path = _local_cookies
            else:
                cookies_path = os.environ.get('COOKIES_FILE', '/tmp/cookies.txt')
            
            cookies_info = {
                "path": cookies_path,
                "exists": os.path.exists(cookies_path),
                "size": None,
                "readable": False,
                "line_count": 0,
                "netscape_format": False
            }
            
            if cookies_info["exists"]:
                try:
                    stat_info = os.stat(cookies_path)
                    cookies_info["size"] = stat_info.st_size
                    cookies_info["readable"] = os.access(cookies_path, os.R_OK)
                    
                    # Try to read first few lines to validate Netscape format
                    with open(cookies_path, 'r') as f:
                        lines = f.readlines()
                        cookies_info["line_count"] = len(lines)
                        # Netscape format starts with "# Netscape HTTP Cookie File"
                        if lines and '# Netscape HTTP Cookie File' in lines[0]:
                            cookies_info["netscape_format"] = True
                        cookies_info["first_line"] = lines[0].strip() if lines else ""
                except Exception as read_err:
                    cookies_info["read_error"] = str(read_err)
            
            return {"body": cookies_info, "statusCode": 200}
        except Exception as e:
            _log(f'debug/cookies error: {e}')
            return {"body": {"error": str(e)}, "statusCode": 500}

    # Debug endpoint to check Deno JS runtime status
    if path and ('/debug/deno' in path):
        try:
            deno_candidates = [
                os.path.join(os.path.dirname(__file__), 'vendor', 'bin', 'deno'),
                '/tmp/vendor/bin/deno',
                os.path.join(os.getcwd(), 'vendor', 'bin', 'deno'),
                '/tmp/deno/deno',
            ]
            deno_info = {
                "candidates_checked": [],
                "found": False,
                "path": None,
                "executable": False,
                "version": None
            }
            
            for candidate in deno_candidates:
                candidate_info = {
                    "path": candidate,
                    "exists": os.path.isfile(candidate),
                    "executable": os.access(candidate, os.X_OK) if os.path.isfile(candidate) else False
                }
                deno_info["candidates_checked"].append(candidate_info)
                
                if candidate_info["exists"] and candidate_info["executable"]:
                    deno_info["found"] = True
                    deno_info["path"] = candidate
                    deno_info["executable"] = True
                    
                    # Try to get version
                    try:
                        proc = subprocess.run([candidate, '--version'], capture_output=True, text=True, timeout=5)
                        deno_info["version"] = (proc.stdout or '').strip()
                        deno_info["version_rc"] = proc.returncode
                    except Exception as ver_err:
                        deno_info["version_error"] = str(ver_err)
                    break
            
            # Also check PATH
            if not deno_info["found"]:
                import shutil
                path_deno = shutil.which('deno')
                if path_deno:
                    deno_info["found"] = True
                    deno_info["path"] = path_deno
                    deno_info["executable"] = True
                    deno_info["source"] = "PATH"
            
            return {"body": deno_info, "statusCode": 200}
        except Exception as e:
            _log(f'debug/deno error: {e}')
            return {"body": {"error": str(e)}, "statusCode": 500}

    # Debug endpoint to test Deno download at runtime
    if path and ('/debug/deno_download' in path):
        try:
            _log('Testing ensure_deno() download...')
            from serverless_handler_local import ensure_deno
            
            download_result = {
                "started": True,
                "path": None,
                "success": False,
                "logs": []
            }
            
            try:
                js_runtime = ensure_deno(timeout=45)
                download_result["path"] = js_runtime
                download_result["success"] = js_runtime is not None
                
                if js_runtime:
                    # Test the runtime using module-level subprocess (do not re-import here)
                    try:
                        test_proc = subprocess.run([js_runtime, '--version'], capture_output=True, text=True, timeout=5)
                        download_result["version_test"] = {
                            "rc": test_proc.returncode,
                            "stdout": test_proc.stdout.strip(),
                            "stderr": test_proc.stderr.strip()
                        }
                    except Exception as test_err:
                        download_result["version_test_error"] = str(test_err)
                else:
                    download_result["error"] = "ensure_deno() returned None"
            except Exception as dl_err:
                download_result["error"] = str(dl_err)
                import traceback
                download_result["traceback"] = traceback.format_exc()
            
            return {"body": download_result, "statusCode": 200}
        except Exception as e:
            _log(f'debug/deno_download error: {e}')
            return {"body": {"error": str(e)}, "statusCode": 500}

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
                                import shutil, sys as _sys
                                binary_candidate = shutil.which(os.environ.get('YT_DLP_PATH', 'yt-dlp'))
                                if binary_candidate:
                                    cmd = [
                                        binary_candidate,
                                        youtube_url,
                                        "--no-cache-dir",
                                        "--no-check-certificate",
                                        "--dump-single-json",
                                        "--no-playlist",
                                        "-f",
                                        "best[ext=mp4][protocol^=http]/best[protocol^=http]",
                                    ]
                                    _log(f"Running (inline binary): {binary_candidate}")
                                else:
                                    cmd = [
                                        _sys.executable, '-m', 'yt_dlp',
                                        youtube_url,
                                        "--no-cache-dir",
                                        "--no-check-certificate",
                                        "--dump-single-json",
                                        "--no-playlist",
                                        "-f",
                                        "best[ext=mp4][protocol^=http]/best[protocol^=http]",
                                    ]
                                    _log(f"Running (inline python -m yt_dlp): {_sys.executable} -m yt_dlp")
                                
                                # Check for Deno JS runtime - attempt to get or download
                                deno_path = None
                                try:
                                    # Try importing ensure_deno from serverless_handler_local
                                    try:
                                        from serverless_handler_local import ensure_deno
                                        deno_path = ensure_deno()
                                    except ImportError:
                                        # Fallback: check common locations only (no download)
                                        deno_candidates = [
                                            os.path.join(os.path.dirname(__file__), 'vendor', 'bin', 'deno'),
                                            '/tmp/vendor/bin/deno',
                                            os.path.join(os.getcwd(), 'vendor', 'bin', 'deno'),
                                            '/tmp/deno/deno'
                                        ]
                                        for candidate in deno_candidates:
                                            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                                                deno_path = candidate
                                                break
                                        if not deno_path:
                                            import shutil
                                            deno_path = shutil.which('deno')
                                except Exception as de:
                                    _log(f'Error checking for Deno: {de}')

                                if deno_path:
                                    cmd.extend(['--js-runtimes', f'deno:{deno_path}'])
                                    _log(f'🦕 Deno runtime (inline): {deno_path}')
                                
                                # Check local package directory first for cookies
                                _pkg_dir = os.path.dirname(os.path.abspath(__file__))
                                _local_cookies = os.path.join(_pkg_dir, 'cookies.txt')
                                if os.path.exists(_local_cookies):
                                    cookies = _local_cookies
                                else:
                                    cookies = os.environ.get('COOKIES_FILE', '/tmp/cookies.txt')
                                cookies_used = False
                                if os.path.exists(cookies):
                                    cmd.extend(["--cookies", cookies])
                                    cookies_used = True
                                    _log(f"✅ Using cookies (inline): {cookies}")
                                else:
                                    _log(f"⚠️ No cookies file (inline): {cookies}")
                                _log(f"Running (inline): {' '.join(cmd)}")
                                if cookies_used:
                                    _log("🍪 Cookies enabled for this request")
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
                    import shutil, sys as _sys
                    # Prefer a found binary (from YT_DLP_PATH or PATH); otherwise use `python -m yt_dlp`
                    binary_candidate = shutil.which(os.environ.get('YT_DLP_PATH', 'yt-dlp'))
                    if binary_candidate:
                        diag_cmd = [
                            binary_candidate,
                            youtube_url,
                            "--no-cache-dir",
                            "--no-check-certificate",
                            "--dump-single-json",
                            "--no-playlist",
                            "-f",
                            "best[ext=mp4]/best",
                            "-v"
                        ]
                        _log(f"Running diagnostic command (binary): {' '.join(diag_cmd)}")
                    else:
                        diag_cmd = [
                            _sys.executable, '-m', 'yt_dlp',
                            youtube_url,
                            "--no-cache-dir",
                            "--no-check-certificate",
                            "--dump-single-json",
                            "--no-playlist",
                            "-f",
                            "best[ext=mp4]/best",
                            "-v"
                        ]
                        _log(f"Running diagnostic command (python -m yt_dlp): {_sys.executable} -m yt_dlp")
                    
                    # Check for Deno JS runtime - attempt to get or download
                    deno_path = None
                    try:
                        # Try importing ensure_deno from serverless_handler_local
                        try:
                            from serverless_handler_local import ensure_deno
                            deno_path = ensure_deno()
                        except ImportError:
                            # Fallback: check common locations only (no download)
                            deno_candidates = [
                                os.path.join(os.path.dirname(__file__), 'vendor', 'bin', 'deno'),
                                '/tmp/vendor/bin/deno',
                                os.path.join(os.getcwd(), 'vendor', 'bin', 'deno'),
                                '/tmp/deno/deno'
                            ]
                            for candidate in deno_candidates:
                                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                                    deno_path = candidate
                                    break
                            if not deno_path:
                                import shutil
                                deno_path = shutil.which('deno')
                    except Exception as de:
                        _log(f'Error checking for Deno: {de}')

                    if deno_path:
                        diag_cmd.extend(['--js-runtimes', f'deno:{deno_path}'])
                        _log(f'🦕 Diagnostic using Deno: {deno_path}')
                    else:
                        _log('⚠️ No Deno runtime for diagnostic')
                    
                    # Add cookies if available - check local package directory first
                    _pkg_dir = os.path.dirname(os.path.abspath(__file__))
                    _local_cookies = os.path.join(_pkg_dir, 'cookies.txt')
                    if os.path.exists(_local_cookies):
                        cookies_path = _local_cookies
                    else:
                        cookies_path = os.environ.get('COOKIES_FILE', '/tmp/cookies.txt')
                    if os.path.exists(cookies_path):
                        diag_cmd.extend(["--cookies", cookies_path])
                        _log(f"✅ Diagnostic using cookies: {cookies_path}")
                    else:
                        _log(f"⚠️ No cookies for diagnostic: {cookies_path}")
                    
                    env = os.environ.copy()
                    existing_pp = env.get('PYTHONPATH', '')
                    vendor_paths = []
                    for p in ['/tmp/vendor', '/tmp/vendor/lib/python3.11/site-packages', '/tmp/.local/lib/python3.11/site-packages']:
                        try:
                            if os.path.isdir(p):
                                vendor_paths.append(p)
                        except Exception:
                            continue
                    new_pp = os.pathsep.join(vendor_paths) if vendor_paths else ''
                    if new_pp and existing_pp:
                        env['PYTHONPATH'] = new_pp + os.pathsep + existing_pp
                    elif new_pp:
                        env['PYTHONPATH'] = new_pp
                    else:
                        env['PYTHONPATH'] = existing_pp

                    proc = subprocess.run(diag_cmd, capture_output=True, text=True, timeout=int(os.environ.get('REQUEST_TIMEOUT', '45')), env=env)
                    stderr = proc.stderr or ''
                    stdout = proc.stdout or ''
                    _log(f"Diagnostic rc={proc.returncode} stderr={(stderr[:300]).replace(chr(10),' ')}")
                    
                    # Parse stderr for common YouTube protection patterns and provide helpful messages
                    error_msg = "Failed to extract stream"
                    error_reason = None
                    stderr_lower = stderr.lower()
                    
                    # Check if cookies were found to provide more context
                    cookies_found = 'found youtube account cookies' in stderr_lower
                    
                    if 'signature solving failed' in stderr_lower or 'n challenge solving' in stderr_lower:
                        if cookies_found:
                            error_reason = "Video requires JavaScript runtime for signature solving (cookies loaded successfully but JS runtime unavailable). Try a different video or enable JS runtime support."
                        else:
                            error_reason = "YouTube signature solving requires a JavaScript runtime (deno/node/bun/quickjs) which is not available on this serverless environment."
                    elif 'login_required' in stderr_lower or 'sign in to confirm' in stderr_lower:
                        error_reason = "YouTube requires authentication/cookies for this video. This video may be age-restricted or region-locked."
                    elif 'no supported javascript runtime' in stderr_lower or 'js runtimes: none' in stderr_lower:
                        error_reason = "YouTube extraction requires a JavaScript runtime (deno/node/bun/quickjs) which is not available on this serverless environment."
                    elif 'members-only content' in stderr_lower:
                        error_reason = "This video is members-only and requires channel membership."
                    elif 'video unavailable' in stderr_lower or 'this video is unavailable' in stderr_lower:
                        error_reason = "Video is unavailable (may be private, deleted, or region-restricted)."
                    elif proc.returncode != 0 and not stdout.strip():
                        error_reason = "yt-dlp extraction failed. Check diagnostic stderr for details."
                    
                    # Include any Python import error in the diagnostic if present
                    py_import_err = None
                    try:
                        import serverless_handler_local as _shl
                        py_import_err = getattr(_shl, 'PY_IMPORT_ERROR', None)
                    except Exception as e:
                        py_import_err = f'import error reading PY_IMPORT_ERROR: {e}'
                    
                    diagnostic = {"rc": proc.returncode, "stderr": stderr[:2000], "stdout_sample": stdout[:2000]}
                    if py_import_err:
                        diagnostic['python_import_error'] = py_import_err
                    
                    body = {"error": error_msg, "diagnostic": diagnostic}
                    if error_reason:
                        body['reason'] = error_reason
                    
                    return {"body": body, "statusCode": 500}
                except Exception as de:
                    _log(f'Diagnostic run failed: {de}')
                    return {"body": {"error": "Failed to extract stream", "diagnostic_error": str(de)}, "statusCode": 500}
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            _log(f'extraction error: {e} -- trace: {tb}')
            return {"body": {"error": str(e), "type": type(e).__name__, "traceback": tb}, "statusCode": 500}

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
