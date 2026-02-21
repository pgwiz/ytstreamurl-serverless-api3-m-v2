#!/usr/bin/env python3
"""
YouTube Stream Extractor API with Playground UI
Uses proven yt-dlp logic with proper subprocess invocation and cookie support
"""
import os
import sys
import json
import subprocess
import shutil
import tempfile
import threading
from datetime import datetime
from functools import lru_cache
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from urllib.parse import quote

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Configuration
LOG_DIR = os.environ.get('LOG_DIR', '/tmp/proxyLogs')
# Check multiple locations for cookies (Docker, Koyeb, local)
COOKIES_FILE = os.environ.get('COOKIES_FILE') or os.path.exists('/app/cookies.txt') and '/app/cookies.txt' or '/tmp/cookies.txt'
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '60'))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get('PORT', '5000'))

os.makedirs(LOG_DIR, exist_ok=True)

# --- FIXED: Cookie Management ---
COOKIE_MANAGER = {
    'path': None,
    'loaded': False
}

def log(msg):
    """Log messages to stdout and file"""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{ts}] {msg}"
    print(log_line, flush=True)
    
    try:
        log_file = os.path.join(LOG_DIR, f"api_{datetime.now().strftime('%Y-%m-%d')}.log")
        with open(log_file, 'a') as f:
            f.write(log_line + '\n')
    except:
        pass

def get_cookie_file_path():
    """Get or create cookie file path (reuse existing if available)."""
    global COOKIE_MANAGER
    
    if COOKIE_MANAGER['loaded'] and COOKIE_MANAGER['path'] and os.path.exists(COOKIE_MANAGER['path']):
        return COOKIE_MANAGER['path']
    
    # Check multiple possible locations
    possible_paths = [
        '/app/cookies.txt',           # Docker image location
        '/tmp/cookies.txt',           # Docker compose mount
        COOKIES_FILE,                 # Environment variable
        'cookies.txt'                 # Local directory
    ]
    
    # Return first existing path
    for path in possible_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding='utf-8') as f:
                    cookie_data = f.read()
                if cookie_data.strip():
                    temp_dir = tempfile.gettempdir()
                    cookie_path = os.path.join(temp_dir, "yt_cookies_reusable.txt")
                    
                    if not os.path.exists(cookie_path):
                        with open(cookie_path, "w", encoding='utf-8') as f:
                            f.write(cookie_data)
                    
                    COOKIE_MANAGER['path'] = cookie_path
                    COOKIE_MANAGER['loaded'] = True
                    log(f'🍪 Cookies loaded from: {path} ({len(cookie_data)} bytes)')
                    return cookie_path
            except Exception as e:
                log(f'⚠️ Failed to load cookies from {path}: {e}')
                continue
    
    # Try environment variable
    cookie_data = os.environ.get("YTDLP_COOKIES")
    if cookie_data:
        try:
            temp_dir = tempfile.gettempdir()
            cookie_path = os.path.join(temp_dir, "yt_cookies_reusable.txt")
            
            if not os.path.exists(cookie_path):
                with open(cookie_path, "w", encoding='utf-8') as f:
                    f.write(cookie_data)
            
            COOKIE_MANAGER['path'] = cookie_path
            COOKIE_MANAGER['loaded'] = True
            log(f'🍪 Cookies loaded from environment (YTDLP_COOKIES)')
            return cookie_path
        except Exception as e:
            log(f'⚠️ Cookie loading from env failed: {e}')
    
    log('⚠️ No cookies found - authentication may be required')
    return None

def extract_youtube_stream(video_id):
    """Extract YouTube stream URL using yt-dlp subprocess (proven method)"""
    try:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Build yt-dlp command using sys.executable -m (most reliable)
        cmd = [
            sys.executable, "-m", "yt_dlp",
            youtube_url,
            '--no-cache-dir',
            '--no-check-certificate',
            '--dump-single-json',
            '--no-playlist',
            '-f', 'best[ext=mp4][protocol^=http]/best[protocol^=http]'
        ]
        
        # Add Node.js as JS runtime for signature solving (installed in Docker)
        # yt-dlp now requires explicit --js-runtimes for Node.js
        node_path = shutil.which('node')
        if node_path:
            cmd.extend(['--js-runtimes', f'node'])  # Just "node", let it find the path
            log(f'📦 Using Node.js JS runtime from: {node_path}')
        else:
            # Fallback: try common paths
            for path in ['/usr/bin/node', '/usr/local/bin/node', '/bin/node']:
                if os.path.exists(path):
                    cmd.extend(['--js-runtimes', 'node'])
                    log(f'📦 Using Node.js JS runtime from: {path}')
                    break
            else:
                log('⚠️ Node.js not found - some videos may fail')
        
        # Add cookies if available
        cookie_path = get_cookie_file_path()
        if cookie_path:
            cmd.extend(['--cookies', cookie_path])
        
        log(f'🎬 Extracting video: {video_id}')
        log(f'📋 Command: {" ".join(cmd[:4])}...')  # Log first few args for debugging
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT)
        
        if result.returncode != 0:
            log(f'❌ yt-dlp failed: {result.stderr[:300]}')
            return None
        
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            log(f'❌ JSON parse error: {e}')
            log(f'📝 stdout: {result.stdout[:200]}')
            return None
        
        stream_url = data.get('url')
        if not stream_url:
            log(f'❌ No stream URL found in response')
            log(f'📝 Response keys: {list(data.keys())}')
            return None
        
        log(f'✅ Successfully extracted: {data.get("title", "Unknown")}')
        return {
            'title': data.get('title', 'Unknown'),
            'url': stream_url,
            'thumbnail': data.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
            'duration': data.get('duration', 0),
            'uploader': data.get('uploader', 'Unknown'),
            'view_count': data.get('view_count', 0),
            'id': video_id,
            'videoId': video_id,
            'ext': data.get('ext', 'mp4')
        }
    except subprocess.TimeoutExpired:
        log(f'❌ Extraction timeout ({REQUEST_TIMEOUT}s)')
        return None
    except Exception as e:
        log(f'❌ Extraction error: {str(e)}')
        return None

@lru_cache(maxsize=128)
def search_youtube(query, limit=5):
    """Search YouTube using yt-dlp subprocess (proven method)"""
    try:
        # Use subprocess with sys.executable -m for reliable execution
        command = [
            sys.executable, "-m", "yt_dlp",
            f"ytsearch{limit}:{query}",
            "--dump-single-json",
            "--flat-playlist",
            "--no-cache-dir"
        ]
        
        # Add cookies if available
        cookie_path = get_cookie_file_path()
        if cookie_path:
            command.extend(["--cookies", cookie_path])
        
        process = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
        
        if process.returncode != 0:
            log(f'⚠️ Search failed: {process.stderr[:200]}')
            return []
        
        data = json.loads(process.stdout)
        
        results = []
        if 'entries' in data:
            for entry in data['entries'][:limit]:
                if entry:
                    results.append({
                        'videoId': entry.get('id', ''),
                        'id': entry.get('id', ''),
                        'title': entry.get('title', 'Unknown Title'),
                        'name': entry.get('title', 'Unknown Title'),
                        'duration': entry.get('duration_string', 'Unknown'),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                        'thumbnail': entry.get('thumbnail', f"https://img.youtube.com/vi/{entry.get('id', '')}/mqdefault.jpg"),
                        'uploader': entry.get('uploader', 'Unknown'),
                        'artist': entry.get('uploader', 'Unknown')
                    })
        
        log(f'✅ Search found {len(results)} results for: {query}')
        return results
    except Exception as e:
        log(f'Search error: {e}')
        return []

@app.route('/')
def index():
    """Serve the playground UI"""
    return send_from_directory('static', 'playground.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'youtube-stream-api'})

@app.route('/api/stream/<video_id>')
def get_stream(video_id):
    """Extract YouTube stream URL"""
    if not video_id or len(video_id) < 10:
        return jsonify({'error': 'Invalid video ID'}), 400
    
    result = extract_youtube_stream(video_id)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({
            'error': 'Failed to extract stream',
            'video_id': video_id,
            'reason': 'Video may be unavailable, require authentication, or need JavaScript runtime support'
        }), 400

@app.route('/api/search/youtube')
def search():
    """Search YouTube"""
    query = request.args.get('q') or request.args.get('query')
    if not query:
        return jsonify({'error': 'Missing query parameter'}), 400
    
    limit = min(int(request.args.get('limit', 5)), 20)
    results = search_youtube(query, limit=limit)
    
    return jsonify({'results': results, 'count': len(results)})

@app.route('/api/status')
def status():
    """API status endpoint"""
    node_available = bool(shutil.which('node'))
    cookies_available = os.path.exists(COOKIES_FILE)
    
    return jsonify({
        'service': 'YouTube Stream Extractor API',
        'version': '1.0.0',
        'node_js': node_available,
        'cookies': cookies_available,
        'log_dir': LOG_DIR,
        'timeout': REQUEST_TIMEOUT,
        'port': PORT
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    log(f'🚀 Starting YouTube Stream API on port {PORT}')
    log(f'Node.js available: {bool(shutil.which("node"))}')
    log(f'Cookies available: {os.path.exists(COOKIES_FILE)}')
    
    # Use gunicorn in production, Flask dev server otherwise
    if os.environ.get('ENV') == 'production':
        os.system(f'gunicorn --bind 0.0.0.0:{PORT} --workers 2 --timeout 120 app:app')
    else:
        app.run(host='0.0.0.0', port=PORT, debug=False)
