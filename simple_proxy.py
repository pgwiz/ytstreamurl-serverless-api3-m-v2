import socket
import select
import threading
import sys
import os
import json
import subprocess
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Log directory
LOG_DIR = "/root/proxyLogs"
os.makedirs(LOG_DIR, exist_ok=True)

# Store recent yt-dlp execution logs (last 10)
ytdlp_logs = []

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {msg}"
    print(log_line, flush=True)
    
    # Also write to file (daily log)
    log_file = os.path.join(LOG_DIR, f"proxy_{datetime.now().strftime('%Y-%m-%d')}.log")
    try:
        with open(log_file, 'a') as f:
            f.write(log_line + '\n')
    except:
        pass

# Configuration
BIND_HOST = '::'  # Bind to all interfaces (IPv4 + IPv6 dual-stack)
BIND_PORT = 6178
BUFFER_SIZE = 8192
COOKIES_FILE = "/root/cookies.txt"  # Path to YouTube cookies

def extract_youtube_stream(video_id):
    """Extract YouTube stream URL using yt-dlp (Reference Implementation Logic)"""
    global ytdlp_logs
    log_entry = {"video_id": video_id, "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "stdout": "", "stderr": "", "success": False}
    
    try:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Explicitly use python3.11 to run yt-dlp
        # Arguments adapted from old/index.py for proven reliability
        cmd = [
            "python3.11", 
            "/usr/local/bin/yt-dlp",
            youtube_url,
            "--no-cache-dir",
            "--no-check-certificate",
            "--dump-single-json",
            "--no-playlist",
            "-f", "best[ext=mp4]/best" # Let yt-dlp choose best format
        ]
        
        # Add cookies if file exists
        if os.path.exists(COOKIES_FILE):
            cmd.extend(["--cookies", COOKIES_FILE])
        
        log(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45) # Increased timeout
        
        log_entry["stdout"] = result.stdout[:1000]
        log_entry["stderr"] = result.stderr[:1000]
        
        if result.returncode != 0:
            log(f"yt-dlp error (code {result.returncode}): {result.stderr[:200]}")
            ytdlp_logs.append(log_entry)
            if len(ytdlp_logs) > 10:
                ytdlp_logs.pop(0)
            return None
        
        data = json.loads(result.stdout)
        
        # Direct extraction - trusting yt-dlp's selection via -f flag
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

class ProxyServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        # Use IPv6 socket with dual-stack (also accepts IPv4)
        self.server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Allow IPv4 connections on this IPv6 socket
        self.server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(100)
            print(f"[*] Proxy Server started on {self.host}:{self.port}")
            print(f"[*] Use this IP/Domain in your Vercel PROXY env var: http://<YOUR_SERVER_IP>:{self.port}")
            
            while True:
                client_socket, addr = self.server_socket.accept()
                # Log EVERY connection immediately for debugging
                log(f"🔌 RAW CONNECTION from {addr[0]}:{addr[1]}")
                client_handler = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                client_handler.daemon = True
                client_handler.start()
        except Exception as e:
            print(f"[!] Error: {e}")
        finally:
            self.server_socket.close()

    def handle_client(self, client_socket, addr):
        try:
            request = client_socket.recv(BUFFER_SIZE)
            if not request:
                log("⚠️ Empty request received, closing")
                client_socket.close()
                return

            first_line = request.split(b'\n')[0]
            log(f"📨 FIRST LINE: {first_line[:100]}")  # Log method and path
            
            # Extract Real IP from Nginx Headers
            real_ip = addr[0]
            trace_id = ""
            for line in request.split(b'\n'):
                if line.lower().startswith(b'x-real-ip:'):
                    real_ip = line.split(b':', 1)[1].strip().decode('utf-8', errors='ignore')
                elif line.lower().startswith(b'x-forwarded-for:'):
                    real_ip = line.split(b':', 1)[1].strip().split(b',')[0].strip().decode('utf-8', errors='ignore')
                elif line.lower().startswith(b'x-proxy-trace-id:'):
                    trace_id = line.split(b':', 1)[1].strip().decode('utf-8', errors='ignore')

            # Check for API endpoint: /api/stream/<video_id>
            if b'GET /api/stream/' in first_line:
                try:
                    path = first_line.split(b' ')[1].decode('utf-8')
                    video_id = path.split('/api/stream/')[1].split('?')[0]
                    log(f"🎥 API Request: /api/stream/{video_id} from {real_ip}")
                    
                    result = extract_youtube_stream(video_id)
                    
                    if result:
                        response_body = json.dumps(result).encode('utf-8')
                        response = (
                            b"HTTP/1.1 200 OK\r\n"
                            b"Content-Type: application/json\r\n"
                            b"Access-Control-Allow-Origin: *\r\n"
                            b"Connection: close\r\n"
                            b"Content-Length: " + str(len(response_body)).encode() + b"\r\n\r\n"
                            + response_body
                        )
                        log(f"✅ Stream extracted for {video_id}")
                    else:
                        error_body = json.dumps({"error": "Failed to extract stream"}).encode('utf-8')
                        response = (
                            b"HTTP/1.1 500 Internal Server Error\r\n"
                            b"Content-Type: application/json\r\n"
                            b"Connection: close\r\n"
                            b"Content-Length: " + str(len(error_body)).encode() + b"\r\n\r\n"
                            + error_body
                        )
                        log(f"❌ Failed to extract stream for {video_id}")
                    
                    client_socket.send(response)
                    client_socket.close()
                    return
                except Exception as e:
                    log(f"❌ API Error: {e}")
                    error_body = json.dumps({"error": str(e)}).encode('utf-8')
                    response = (
                        b"HTTP/1.1 500 Internal Server Error\r\n"
                        b"Content-Type: application/json\r\n"
                        b"Connection: close\r\n"
                        b"Content-Length: " + str(len(error_body)).encode() + b"\r\n\r\n"
                        + error_body
                    )
                    client_socket.send(response)
                    client_socket.close()
                    return

            # Log connection now with real IP and Trace ID
            if not (b'GET /health' in first_line or b'GET / HTTP' in first_line):
                 log_msg = f"📥 Request from {real_ip}"
                 if trace_id:
                     log_msg += f" [Trace: {trace_id}]"
                 log(log_msg)
            
            # --- Health Check Endpoint ---
            if b'GET /health' in first_line or b'GET / HTTP' in first_line:
                host_header = b''
                for line in request.split(b'\n'):
                    if line.lower().startswith(b'host:'):
                        # Get everything after "Host: " (handle Host: localhost:6178)
                        host_header = line.split(b':', 1)[1].strip().lower()
                        break
                # If the Host header points to our proxy (localhost, 127.x, :6178, or known domains)
                # Add your proxy domain here for direct response
                is_local = b'localhost' in host_header or b'127.' in host_header or b':2082' in host_header
                is_proxy_domain = b'servx.pgwiz.us.kg' in host_header or b'pgwiz' in host_header
                
                if is_local or is_proxy_domain:
                    # Read recent logs
                    log_content = ""
                    log_file = os.path.join(LOG_DIR, f"proxy_{datetime.now().strftime('%Y-%m-%d')}.log")
                    try:
                        with open(log_file, 'r') as f:
                            lines = f.readlines()
                            log_content = ''.join(lines[-50:])  # Last 50 lines
                    except:
                        log_content = "(No logs yet)"
                    
                    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Proxy Server</title>
<style>
body {{ font-family: monospace; background: #1a1a2e; color: #0f0; padding: 20px; }}
h1 {{ color: #4ade80; }}
.status {{ color: #4ade80; font-size: 24px; margin: 20px 0; }}
pre {{ background: #0d0d1a; padding: 15px; border-radius: 8px; overflow-x: auto; max-height: 400px; overflow-y: auto; }}
button {{ background: #4ade80; color: #000; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }}
button:hover {{ background: #22c55e; }}
</style></head><body>
<h1>🌐 Proxy Server</h1>
<div class="status">✅ Proxy Server is Alive</div>
<p><strong>Port:</strong> 2082 | <strong>Logs:</strong> /root/proxyLogs/</p>
<button onclick="navigator.clipboard.writeText('http://servx.pgwiz.us.kg:2082')">📋 Copy Proxy URL</button>
<button onclick="location.reload()">🔄 Refresh</button>
<h3>📜 Recent Logs (Last 50)</h3>
<pre id="logs">{log_content}</pre>
<script>setTimeout(()=>location.reload(), 10000);</script>
</body></html>'''
                    
                    response = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n{html}".encode()
                    client_socket.send(response)
                    client_socket.close()
                    return
            
            url = first_line.split(b' ')[1]
            http_pos = url.find(b'://')
            
            if http_pos == -1:
                temp = url
            else:
                temp = url[(http_pos + 3):]

            port_pos = temp.find(b':')
            webserver_pos = temp.find(b'/')
            
            if webserver_pos == -1:
                webserver_pos = len(temp)

            webserver = ""
            port = -1

            if port_pos == -1 or webserver_pos < port_pos:
                port = 80
                webserver = temp[:webserver_pos]
            else:
                port = int((temp[(port_pos + 1):])[:webserver_pos - port_pos - 1])
                webserver = temp[:port_pos]

            if b'CONNECT' in first_line:
                log(f"🔒 HTTPS CONNECT → {webserver.decode()}:{port} [IP: {real_ip}]")
                self.handle_https_tunnel(client_socket, webserver, port)
            else:
                log(f"🌐 HTTP {first_line.split(b' ')[0].decode()} → {webserver.decode()}:{port} [IP: {real_ip}]")
                self.handle_http_request(client_socket, request, webserver, port)

        except Exception as e:
            log(f"❌ Error processing request from {addr[0]}: {e}")
            client_socket.close()

    def handle_https_tunnel(self, client_socket, host, port):
        try:
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((host, port))
            log(f"✅ CONNECT 200 → {host.decode()}:{port}")
            client_socket.send(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            
            self.forward_data(client_socket, remote_socket)
        except Exception as e:
            log(f"❌ CONNECT FAILED → {host.decode()}:{port} - {e}")
            # print(f"[!] HTTPS Tunnel Error: {e}")
            client_socket.close()

    def handle_http_request(self, client_socket, request, host, port):
        try:
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((host, port))
            remote_socket.send(request)
            
            self.forward_data(client_socket, remote_socket)
        except Exception as e:
            # print(f"[!] HTTP Request Error: {e}")
            client_socket.close()
            if 'remote_socket' in locals():
                remote_socket.close()

    def forward_data(self, client, remote):
        try:
            sockets = [client, remote]
            while True:
                readable, _, _ = select.select(sockets, [], [], 60)
                if not readable:
                    break
                
                for sock in readable:
                    other = remote if sock is client else client
                    data = sock.recv(BUFFER_SIZE)
                    if not data:
                        return
                    other.send(data)
        except:
            pass
        finally:
            client.close()
            remote.close()

if __name__ == '__main__':
    proxy = ProxyServer(BIND_HOST, BIND_PORT)
    proxy.start()
