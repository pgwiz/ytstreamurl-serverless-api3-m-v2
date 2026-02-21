#!/usr/bin/env python3
"""
YouTube Stream Extractor API with Playground UI
Includes inline youtube_extractor logic to avoid import issues in Docker
"""
import os
import sys
import json
import subprocess
import shutil
import tempfile
import requests
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from urllib.parse import quote, unquote

app = Flask(__name__, static_url_path='/static', static_folder='static')

# ===== INLINE: YoutubeExtractor Class =====
class YoutubeExtractor:
    """Shared YouTube extraction logic for serverless and web apps"""
    
    def __init__(self, cookies_file=None, timeout=60, log_func=None):
        self.cookies_file = cookies_file
        self.timeout = timeout
        self.log_func = log_func or self._default_log
        self.cookie_manager = {'path': None, 'loaded': False}
    
    def _default_log(self, msg):
        print(f"[YT] {msg}", flush=True)
    
    def log(self, msg):
        self.log_func(msg)
    
    def get_cookie_file_path(self):
        """Get or create cookie file path (reuse existing if available)."""
        if self.cookie_manager['loaded'] and self.cookie_manager['path'] and os.path.exists(self.cookie_manager['path']):
            return self.cookie_manager['path']
        
        possible_paths = [
            self.cookies_file, '/app/cookies.txt', '/tmp/cookies.txt', 'cookies.txt'
        ]
        
        self.log(f'🔍 DEBUG: COOKIES_FILE env var: {self.cookies_file}')
        self.log(f'🔍 DEBUG: Current working directory: {os.getcwd()}')
        self.log(f'🔍 DEBUG: Searching for cookies in: {possible_paths}')
        
        for path in possible_paths:
            self.log(f'🔍 DEBUG: Checking {path} - exists: {path and os.path.exists(path)}')
            if path:
                if os.path.exists(path):
                    self.log(f'✓ Found cookies file at: {path}')
                    try:
                        with open(path, "r", encoding='utf-8') as f:
                            cookie_data = f.read()
                        self.log(f'✓ Successfully read {len(cookie_data)} bytes from {path}')
                        if cookie_data.strip():
                            temp_dir = tempfile.gettempdir()
                            cookie_path = os.path.join(temp_dir, "yt_cookies_runtime.txt")
                            self.log(f'🔍 DEBUG: Creating runtime cookie file at: {cookie_path}')
                            
                            if not os.path.exists(cookie_path):
                                with open(cookie_path, "w", encoding='utf-8') as f:
                                    f.write(cookie_data)
                            
                            self.cookie_manager['path'] = cookie_path
                            self.cookie_manager['loaded'] = True
                            self.log(f'🍪 Cookies loaded from: {path} ({len(cookie_data)} bytes)')
                            return cookie_path
                    except Exception as e:
                        self.log(f'⚠️ Failed to load cookies from {path}: {e}')
                else:
                    self.log(f'✗ {path} does not exist')
            else:
                self.log(f'✗ Path is None')
        
        self.log('🔍 DEBUG: Checking environment variable YTDLP_COOKIES')
        cookie_data = os.environ.get("YTDLP_COOKIES")
        if cookie_data:
            self.log(f'✓ Found YTDLP_COOKIES environment variable ({len(cookie_data)} bytes)')
            try:
                temp_dir = tempfile.gettempdir()
                cookie_path = os.path.join(temp_dir, "yt_cookies_runtime.txt")
                if not os.path.exists(cookie_path):
                    with open(cookie_path, "w", encoding='utf-8') as f:
                        f.write(cookie_data)
                self.cookie_manager['path'] = cookie_path
                self.cookie_manager['loaded'] = True
                self.log(f'🍪 Cookies loaded from environment (YTDLP_COOKIES)')
                return cookie_path
            except Exception as e:
                self.log(f'⚠️ Cookie loading from env failed: {e}')
        else:
            self.log('✗ YTDLP_COOKIES environment variable not set')
        
        self.log('❌ No cookies found - yt-dlp will require authentication for protected videos')
        return None
    
    def search_youtube(self, query, limit=5):
        """Search YouTube using yt-dlp subprocess"""
        try:
            command = [
                sys.executable, "-m", "yt_dlp",
                f"ytsearch{limit}:{query}",
                "--dump-single-json", "--flat-playlist", "--no-cache-dir"
            ]
            
            cookie_path = self.get_cookie_file_path()
            if cookie_path:
                command.extend(["--cookies", cookie_path])
            
            process = subprocess.run(command, capture_output=True, text=True, check=False, timeout=self.timeout)
            
            if process.returncode != 0:
                self.log(f'⚠️ Search failed: {process.stderr[:200]}')
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
            self.log(f'✅ Search found {len(results)} results for: {query}')
            return results
        except subprocess.TimeoutExpired:
            self.log(f'❌ Search timeout ({self.timeout}s)')
            return []
        except Exception as e:
            self.log(f'Search error: {e}')
            return []
    
    def extract_youtube_stream(self, video_id):
        """Extract YouTube stream URL using yt-dlp subprocess"""
        try:
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            cmd = [
                sys.executable, "-m", "yt_dlp", youtube_url,
                '--no-cache-dir', '--no-check-certificate', '--dump-single-json',
                '--no-playlist', '-f', 'best[ext=mp4][protocol^=http]/best[protocol^=http]',
                '--remote-components', 'ejs:github'
            ]
            
            node_path = shutil.which('node')
            if node_path:
                cmd.extend(['--js-runtimes', 'node'])
                self.log(f'📦 Using Node.js JS runtime from: {node_path}')
            else:
                for path in ['/usr/bin/node', '/usr/local/bin/node', '/bin/node']:
                    if os.path.exists(path):
                        cmd.extend(['--js-runtimes', 'node'])
                        self.log(f'📦 Using Node.js JS runtime from: {path}')
                        break
                else:
                    self.log('⚠️ Node.js not found - some videos may fail')
            
            cookie_path = self.get_cookie_file_path()
            if cookie_path:
                cmd.extend(['--cookies', cookie_path])
            
            self.log(f'🎬 Extracting video: {video_id}')
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            
            if result.returncode != 0:
                self.log(f'❌ yt-dlp failed: {result.stderr[:300]}')
                return None
            
            data = json.loads(result.stdout)
            stream_url = data.get('url')
            if not stream_url:
                self.log(f'❌ No stream URL found in response')
                return None
            
            self.log(f'✅ Successfully extracted: {data.get("title", "Unknown")}')
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
            self.log(f'❌ Extraction timeout ({self.timeout}s)')
            return None
        except Exception as e:
            self.log(f'❌ Extraction error: {str(e)}')
            return None

# ===== END: YoutubeExtractor Class =====

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
    """Extract YouTube stream URL (GET)"""
    if not video_id or len(video_id) < 10:
        return jsonify({'error': 'Invalid video ID'}), 400
    
    result = extract_youtube_stream(video_id)
    
    if result:
        # Add encoded proxy URL for server-side streaming
        stream_url = result.get('url', '')
        if stream_url:
            encoded_url = base64.b64encode(stream_url.encode()).decode()
            result['proxy_url'] = f"/stream/play?url={encoded_url}"
            result['proxy_url_encoded'] = encoded_url
        
        return jsonify(result)
    else:
        return jsonify({
            'error': 'Failed to extract stream',
            'video_id': video_id,
            'reason': 'Video may be unavailable, require authentication, or need JavaScript runtime support'
        }), 400

@app.route('/stream/<video_id>', methods=['POST'])
def post_stream(video_id):
    """Extract YouTube stream URL and return with encoded proxy URL (POST)"""
    if not video_id or len(video_id) < 10:
        return jsonify({'error': 'Invalid video ID'}), 400
    
    result = extract_youtube_stream(video_id)
    
    if result:
        # Add encoded proxy URL for server-side streaming
        stream_url = result.get('url', '')
        if stream_url:
            encoded_url = base64.b64encode(stream_url.encode()).decode()
            result['proxy_url'] = f"/stream/play?url={encoded_url}"
            result['proxy_url_encoded'] = encoded_url
            result['message'] = f"Video extracted successfully. Use proxy_url for server-side streaming."
        
        return jsonify(result), 200
    else:
        return jsonify({
            'error': 'Failed to extract stream',
            'video_id': video_id,
            'reason': 'Video may be unavailable, require authentication, or need JavaScript runtime support'
        }), 400

@app.route('/api/proxy/<video_id>')
def proxy_stream(video_id):
    """Proxy YouTube stream through server (for CORS and playback support) - DEPRECATED"""
    if not video_id or len(video_id) < 10:
        return jsonify({'error': 'Invalid video ID'}), 400
    
    try:
        result = extract_youtube_stream(video_id)
        if not result or not result.get('url'):
            return jsonify({'error': 'Failed to extract stream'}), 400
        
        stream_url = result['url']
        response = requests.get(stream_url, stream=True, timeout=30)
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch stream from YouTube'}), 502
        
        return response.content, 200, {
            'Content-Type': response.headers.get('content-type', 'video/mp4'),
            'Content-Length': response.headers.get('content-length', ''),
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'no-cache',
            'Access-Control-Allow-Origin': '*'
        }
    except Exception as e:
        log(f'❌ Proxy error: {str(e)}')
        return jsonify({'error': 'Proxy failed', 'message': str(e)}), 500

@app.route('/stream/play')
def stream_play():
    """Proxy any stream URL through the server - streaming endpoint"""
    stream_url = request.args.get('url')
    if not stream_url:
        return jsonify({'error': 'Missing url parameter'}), 400
    
    try:
        # Decode the stream URL (could be base64 or URL-encoded)
        try:
            decoded_url = base64.b64decode(stream_url).decode('utf-8')
        except:
            try:
                decoded_url = unquote(stream_url)
            except:
                decoded_url = stream_url
        
        log(f'🔄 Proxying stream from: {decoded_url[:80]}...')
        response = requests.get(decoded_url, stream=True, timeout=60)
        
        if response.status_code != 200:
            log(f'❌ Stream error: {response.status_code}')
            return jsonify({'error': f'Stream error: {response.status_code}'}), 502
        
        log(f'✅ Streaming video...')
        
        # Stream the response back to the client
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        return generate(), 200, {
            'Content-Type': response.headers.get('content-type', 'video/mp4'),
            'Content-Length': response.headers.get('content-length', ''),
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'public, max-age=3600',
            'Access-Control-Allow-Origin': '*'
        }
    except Exception as e:
        log(f'❌ Stream proxy error: {str(e)}')
        return jsonify({'error': 'Stream failed', 'message': str(e)}), 500

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
    log(f'📁 Working directory: {os.getcwd()}')
    log(f'🔍 Directory contents: {os.listdir(".")[:10]}')
    log(f'Node.js available: {bool(shutil.which("node"))}')
    
    # Debug: List files in key locations
    for debug_path in ['/app', '/app/static', '/tmp']:
        if os.path.exists(debug_path):
            try:
                files = os.listdir(debug_path)
                log(f'📂 {debug_path}: {files[:10]}')
            except:
                log(f'❌ Cannot list {debug_path}')
        else:
            log(f'❌ {debug_path} does not exist')
    
    # Check cookies using extractor's method (with debug output)
    cookies_path = extractor.get_cookie_file_path()
    log(f'Cookies available: {bool(cookies_path)} ({cookies_path if cookies_path else "not found"})')
    
    # Use gunicorn in production, Flask dev server otherwise
    if os.environ.get('ENV') == 'production':
        os.system(f'gunicorn --bind 0.0.0.0:{PORT} --workers 2 --timeout 120 app:app')
    else:
        app.run(host='0.0.0.0', port=PORT, debug=False)
