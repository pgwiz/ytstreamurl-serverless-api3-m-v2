#!/usr/bin/env python3
"""
YouTube Stream Extractor API with Playground UI
Uses simple_proxy.py extraction logic with Flask + Node.js for JS runtime support
"""
import os
import sys
import json
import subprocess
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from urllib.parse import quote

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Configuration
LOG_DIR = os.environ.get('LOG_DIR', '/tmp/proxyLogs')
COOKIES_FILE = os.environ.get('COOKIES_FILE', '/tmp/cookies.txt')
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '60'))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get('PORT', '5000'))

os.makedirs(LOG_DIR, exist_ok=True)

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

def extract_youtube_stream(video_id):
    """Extract YouTube stream URL using yt-dlp (simple_proxy.py method)"""
    try:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Build yt-dlp command
        cmd = [
            'yt-dlp',
            youtube_url,
            '--no-cache-dir',
            '--no-check-certificate',
            '--dump-single-json',
            '--no-playlist',
            '-f', 'best[ext=mp4][protocol^=http]/best[protocol^=http]'
        ]
        
        # Add Node.js as JS runtime for signature solving (installed in Docker)
        node_path = shutil.which('node')
        if node_path:
            cmd.extend(['--js-runtimes', f'node:{node_path}'])
            log(f'📦 Using Node.js JS runtime: {node_path}')
        else:
            log('⚠️  Node.js not found - some videos may fail')
        
        # Add cookies if file exists
        if os.path.exists(COOKIES_FILE):
            cmd.extend(['--cookies', COOKIES_FILE])
            log(f'🍪 Using cookies from: {COOKIES_FILE}')
        
        log(f'🎬 Extracting video: {video_id}')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT)
        
        if result.returncode != 0:
            log(f'❌ yt-dlp failed: {result.stderr[:200]}')
            return None
        
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            log(f'❌ JSON parse error: {e}')
            return None
        
        stream_url = data.get('url')
        if not stream_url:
            log(f'❌ No stream URL found')
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

def search_youtube(query, limit=5):
    """Search YouTube using yt-dlp ytsearch"""
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'nocheckcertificate': True,
            'socket_timeout': 30
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            data = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        
        entries = data.get('entries', []) if isinstance(data, dict) else []
        results = []
        for entry in entries:
            if entry:
                results.append({
                    'id': entry.get('id'),
                    'title': entry.get('title'),
                    'duration': entry.get('duration', 0),
                    'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                    'thumbnail': entry.get('thumbnail'),
                    'uploader': entry.get('uploader', 'Unknown')
                })
        
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
