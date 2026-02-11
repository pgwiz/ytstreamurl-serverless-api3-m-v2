"""
DigitalOcean Serverless Function Handler
Wrapper for YouTube Stream URL extraction and proxying
"""

import json
import subprocess
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs, quote
from flask import Flask, request, jsonify, Response
import requests

app = Flask(__name__)

# Configuration
COOKIES_FILE = os.environ.get('COOKIES_FILE', '/tmp/cookies.txt')
YT_DLP_PATH = os.environ.get('YT_DLP_PATH', 'yt-dlp')
LOG_DIR = os.environ.get('LOG_DIR', '/tmp/proxyLogs')
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '45'))

os.makedirs(LOG_DIR, exist_ok=True)

# Store recent yt-dlp execution logs (last 10)
ytdlp_logs = []

def log(msg):
    """Log message to stdout and file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {msg}"
    print(log_line, flush=True)
    
    try:
        log_file = os.path.join(LOG_DIR, f"proxy_{datetime.now().strftime('%Y-%m-%d')}.log")
        with open(log_file, 'a') as f:
            f.write(log_line + '\n')
    except:
        pass

def extract_youtube_stream(video_id):
    """Extract YouTube stream URL using yt-dlp"""
    global ytdlp_logs
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
            "-f", "best[ext=mp4][protocol^=http]/best[protocol^=http]"
        ]
        
        # Add cookies if file exists
        if os.path.exists(COOKIES_FILE):
            cmd.extend(["--cookies", COOKIES_FILE])
        
        log(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=REQUEST_TIMEOUT)
        
        log_entry["stdout"] = result.stdout[:1000]
        log_entry["stderr"] = result.stderr[:1000]
        
        if result.returncode != 0:
            log(f"yt-dlp error (code {result.returncode}): {result.stderr[:200]}")
            ytdlp_logs.append(log_entry)
            if len(ytdlp_logs) > 10:
                ytdlp_logs.pop(0)
            return None
        
        data = json.loads(result.stdout)
        stream_url = data.get('url')
        
        if not stream_url:
            log("No URL found in yt-dlp output")
            ytdlp_logs.append(log_entry)
            if len(ytdlp_logs) > 10:
                ytdlp_logs.pop(0)
            return None
            
        log_entry["success"] = True
        ytdlp_logs.append(log_entry)
        if len(ytdlp_logs) > 10:
            ytdlp_logs.pop(0)
        
        return {
            "title": data.get('title', 'Unknown'),
            "url": stream_url,
            "thumbnail": data.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"),
            "duration": str(data.get('duration', 0)),
            "uploader": data.get('uploader', 'Unknown'),
            "id": video_id,
            "videoId": video_id,
            "format_id": data.get('format_id'),
            "ext": data.get('ext', 'mp4')
        }
        
    except subprocess.TimeoutExpired:
        log("yt-dlp timeout")
        log_entry["stderr"] = "Timeout (45s exceeded)"
        ytdlp_logs.append(log_entry)
        if len(ytdlp_logs) > 10:
            ytdlp_logs.pop(0)
        return None
    except Exception as e:
        log(f"Extraction error: {e}")
        log_entry["stderr"] = str(e)
        ytdlp_logs.append(log_entry)
        if len(ytdlp_logs) > 10:
            ytdlp_logs.pop(0)
        return None

@app.route('/api/stream/<video_id>', methods=['GET'])
def get_stream(video_id):
    """Extract and return YouTube stream URL"""
    log(f"🎥 API Request: /api/stream/{video_id} from {request.remote_addr}")
    
    result = extract_youtube_stream(video_id)
    
    if result:
        try:
            original_url = result.get('url')
            if original_url:
                encoded_url = quote(original_url)
                host = request.host.split(':')[0]
                proxy_url = f"https://{host}/streamytlink?url={encoded_url}"
                result['url'] = proxy_url
                result['original_url'] = original_url
                log(f"🔄 Rewrote URL: {proxy_url[:60]}...")
        except Exception as e:
            log(f"⚠️ Rewrite Error: {e}")
        
        log(f"✅ Sent response for {video_id}")
        return jsonify(result), 200
    else:
        log(f"❌ Failed extraction for {video_id}")
        return jsonify({"error": "Failed to extract stream"}), 500

@app.route('/ytdlp', methods=['GET'])
def ytdlp_endpoint():
    """Direct yt-dlp extraction endpoint"""
    video_id = request.args.get('id')
    
    if not video_id:
        return jsonify({"error": "Missing 'id' parameter"}), 400
    
    log(f"🎬 yt-dlp request for video ID: {video_id}")
    result = extract_youtube_stream(video_id)
    
    if result:
        log(f"✅ Sent yt-dlp response for {video_id}")
        return jsonify(result), 200
    else:
        log(f"❌ yt-dlp extraction failed for {video_id}")
        return jsonify({"error": "Failed to extract stream URL"}), 500

@app.route('/stream', methods=['GET'])
@app.route('/streamytlink', methods=['GET'])
def stream_relay():
    """Stream relay/proxy endpoint"""
    target_url = request.args.get('url')
    
    if not target_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400
    
    log(f"📥 Relay Request for: {target_url[:60]}...")
    
    try:
        # Extract range header if present
        headers = {}
        if 'Range' in request.headers:
            headers['Range'] = request.headers['Range']
            log(f"⏩ Forwarding Range: {headers['Range']}")
        
        headers['User-Agent'] = 'Mozilla/5.0'
        
        # Forward the request
        response = requests.get(target_url, headers=headers, stream=True, timeout=REQUEST_TIMEOUT)
        
        # Build response with CORS headers
        def generate():
            try:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            except GeneratorExit:
                pass
        
        return Response(
            generate(),
            status=response.status_code,
            headers={
                'Content-Type': response.headers.get('Content-Type', 'video/mp4'),
                'Content-Length': response.headers.get('Content-Length', ''),
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
            }
        )
        
    except Exception as e:
        log(f"❌ Stream Relay Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "youtube-stream-url"}), 200

@app.route('/logs', methods=['GET'])
def get_logs():
    """Get recent yt-dlp logs"""
    return jsonify({"logs": ytdlp_logs}), 200

@app.route('/playground', methods=['GET'])
def playground():
    """Serve the playground UI"""
    playground_path = os.path.join(os.path.dirname(__file__), 'playground.html')
    if os.path.exists(playground_path):
        with open(playground_path, 'r') as f:
            return f.read()
    return "Playground not available", 404

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Local development
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)), debug=False)
