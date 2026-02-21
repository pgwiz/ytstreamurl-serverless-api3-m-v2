#!/usr/bin/env python3
"""
YouTube Stream Extractor API with Playground UI
Uses shared youtube_extractor module for proven extraction logic
"""
import os
import sys
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from urllib.parse import quote

# Import shared extractor module
from youtube_extractor import YoutubeExtractor

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Configuration
LOG_DIR = os.environ.get('LOG_DIR', '/tmp/proxyLogs')
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

# Initialize shared extractor
extractor = YoutubeExtractor(
    cookies_file=os.environ.get('COOKIES_FILE'),
    timeout=int(os.environ.get('REQUEST_TIMEOUT', '60')),
    log_func=log
)

# Use extractor's methods directly
def extract_youtube_stream(video_id):
    """Proxy to extractor"""
    return extractor.extract_youtube_stream(video_id)

def search_youtube(query, limit=5):
    """Proxy to extractor"""
    return extractor.search_youtube(query, limit=limit)

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
    import shutil
    
    node_available = bool(shutil.which('node'))
    cookies_path = extractor.get_cookie_file_path()
    cookies_available = bool(cookies_path)
    
    return jsonify({
        'service': 'YouTube Stream Extractor API',
        'version': '1.0.0',
        'node_js': node_available,
        'cookies': cookies_available,
        'cookies_path': cookies_path or 'Not found',
        'log_dir': LOG_DIR,
        'timeout': extractor.timeout,
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
    import shutil
    
    log(f'🚀 Starting YouTube Stream API on port {PORT}')
    log(f'Node.js available: {bool(shutil.which("node"))}')
    
    # Check cookies using extractor's method
    cookies_path = extractor.get_cookie_file_path()
    log(f'Cookies available: {bool(cookies_path)} ({cookies_path if cookies_path else "not found"})')
    
    # Use gunicorn in production, Flask dev server otherwise
    if os.environ.get('ENV') == 'production':
        os.system(f'gunicorn --bind 0.0.0.0:{PORT} --workers 2 --timeout 120 app:app')
    else:
        app.run(host='0.0.0.0', port=PORT, debug=False)
