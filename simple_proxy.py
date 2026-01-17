import socket
import select
import threading
import sys
import os
import json
import subprocess
from datetime import datetime
from urllib.parse import urlparse, parse_qs, quote

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
            "-f", "best[ext=mp4][protocol^=http]/best[protocol^=http]" # progressive only (no HLS)
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
        
        # Direct extraction
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
                elif line.lower().startswith(b'host:'):
                    current_host = line.split(b':', 1)[1].strip().decode('utf-8', errors='ignore')

            # --- Legacy API Endpoint: /api/stream/<video_id> ---
            if b'GET /api/stream/' in first_line:
                try:
                    path = first_line.split(b' ')[1].decode('utf-8')
                    video_id = path.split('/api/stream/')[1].split('?')[0]
                    log(f"🎥 API Request: /api/stream/{video_id} from {real_ip}")
                    
                    result = extract_youtube_stream(video_id)
                    
                    if result:
                        try:
                            original_url = result.get('url')
                            if original_url:
                                encoded_url = quote(original_url)
                                # Force HTTPS to prevent Mixed Content errors on Vercel
                                proxy_url = f"https://{current_host}/stream?url={encoded_url}"
                                result['url'] = proxy_url
                                result['original_url'] = original_url
                                log(f"🔄 Rewrote URL: {proxy_url[:60]}...")
                        except Exception as rw_err:
                            log(f"⚠️ Rewrite Error: {rw_err}")

                        response_body = json.dumps(result).encode('utf-8')
                        response = (
                            b"HTTP/1.1 200 OK\r\n"
                            b"Content-Type: application/json\r\n"
                            b"Access-Control-Allow-Origin: *\r\n"
                            b"Connection: close\r\n"
                            b"Content-Length: " + str(len(response_body)).encode() + b"\r\n\r\n"
                            + response_body
                        )
                        log(f"✅ sent response for {video_id}")
                    else:
                         error_body = json.dumps({"error": "Failed to extract stream"}).encode('utf-8')
                         response = (b"HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n" + error_body)
                         log(f"❌ Failed extraction for {video_id}")

                    client_socket.send(response)
                    client_socket.close()
                    return
                except Exception as e:
                    log(f"❌ API Error: {e}")
                    client_socket.close()
                    return

            # --- New Stream Relay Endpoint: /stream?url=... ---
            if b'GET /stream' in first_line:
                try:
                    path = first_line.split(b' ')[1].decode('utf-8')
                    parsed = urlparse(path)
                    qs = parse_qs(parsed.query)
                    target_url = qs.get('url', [None])[0]

                    if not target_url:
                        client_socket.send(b"HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nMissing 'url' parameter\r\n")
                        client_socket.close()
                        return

                    log(f"📥 Relay Request for: {target_url[:60]}...")
                    
                    # Use existing proxy logic to forward this specific URL
                    # We can reuse the generic proxy logic by setting 'url' and skipping parsing
                    # But better to call a cleaner handler
                    
                    # Parse target to get host/port
                    target_parsed = urlparse(target_url)
                    hostname = target_parsed.hostname
                    port = target_parsed.port or (443 if target_parsed.scheme == 'https' else 80)
                    
                    # Connect to Upstream (Dual Stack)
                    remote_socket = socket.create_connection((hostname, port), timeout=30)
                    if target_parsed.scheme == 'https':
                        import ssl
                        ctx = ssl.create_default_context()
                        ctx.check_hostname = False
                        ctx.verify_mode = ssl.CERT_NONE
                        remote_socket = ctx.wrap_socket(remote_socket, server_hostname=hostname)

                    # Send Request to Upstream
                    req_path = target_parsed.path
                    if target_parsed.query:
                        req_path += '?' + target_parsed.query
                        
                    req = (f"GET {req_path} HTTP/1.1\r\n"
                           f"Host: {hostname}\r\n"
                           f"User-Agent: Mozilla/5.0\r\n"
                           f"Connection: close\r\n\r\n").encode('utf-8')
                    
                    remote_socket.send(req)
                    
                    # Relay Response
                    self.forward_response_with_cors(remote_socket, client_socket)
                    return
                    
                except Exception as e:
                    log(f"❌ Stream Relay Error: {e}")
                    client_socket.close()
                    return

            # --- yt-dlp Extraction Endpoint: /ytdlp?id=... ---
            if b'GET /ytdlp' in first_line:
                try:
                    path = first_line.split(b' ')[1].decode('utf-8')
                    parsed = urlparse(path)
                    qs = parse_qs(parsed.query)
                    video_id = qs.get('id', [None])[0]

                    if not video_id:
                        client_socket.send(b"HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nMissing 'id' parameter\r\n")
                        client_socket.close()
                        return

                    log(f"🎬 yt-dlp request for video ID: {video_id}")
                    result = extract_youtube_stream(video_id)

                    if not result:
                        client_socket.send(b"HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n" + json.dumps({"error": "Failed to extract stream URL"}).encode('utf-8'))
                        client_socket.close()
                        return
                    
                    try:
                        original_url = result.get('url')
                        if original_url:
                            encoded_url = quote(original_url)
                            # Force HTTPS (since proxy is HTTP)
                            proxy_url = f"https://{current_host}/stream?url={encoded_url}"
                            result['url'] = proxy_url
                            result['original_url'] = original_url
                            
                            log(f"✅ Extracted Original URL: {original_url[:60]}...")
                            log(f"🔄 Rewrote URL for Proxy: {proxy_url}")
                    except Exception as rewrite_err:
                        log(f"⚠️ URL Rewrite Failed: {rewrite_err}")

                    response_body = json.dumps(result).encode('utf-8')
                    response = (
                        b"HTTP/1.1 200 OK\r\n"
                        b"Content-Type: application/json\r\n"
                        b"Access-Control-Allow-Origin: *\r\n"
                        b"Connection: close\r\n"
                        b"Content-Length: " + str(len(response_body)).encode() + b"\r\n\r\n"
                        + response_body
                    )
                    client_socket.send(response)
                    log(f"✅ sent response for {video_id}: {json.dumps(result)}")
                    client_socket.close()
                    return

                except Exception as e:
                    log(f"❌ yt-dlp Endpoint Error: {e}")
                    client_socket.send(b"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n" + str(e).encode('utf-8'))
                    client_socket.close()
                    return

            # --- Stream Relay Endpoint: /stream?url=... ---
            if b'GET /stream' in first_line:
                try:
                    # Parse URL from query string
                    path_str = first_line.split(b' ')[1].decode('utf-8')
                    parsed = urlparse(path_str)
                    qs = parse_qs(parsed.query)
                    target_url = qs.get('url', [None])[0]
                    
                    log(f"🔎 DEBUG: Query: {parsed.query}")
                    if target_url:
                        log(f"🔎 DEBUG: Decoded Target: {target_url}")

                    if not target_url:
                        log("❌ No target URL found in query")
                        client_socket.close()
                        return

                    log(f"🔄 Relaying Stream: {target_url[:50]}...")

                    # Parse target info
                    target_parsed = urlparse(target_url)
                    hostname = target_parsed.hostname
                    port = target_parsed.port or 443
                    target_path = target_parsed.path
                    if target_parsed.query:
                        target_path += "?" + target_parsed.query

                    # Connect to Google Video (Dual Stack Support)
                    # socket.create_connection handles IPv4 and IPv6 resolution automatically
                    remote_socket = socket.create_connection((hostname, port), timeout=30)
                    
                    # If HTTPS (likely), wrap socket
                    if target_parsed.scheme == 'https' or port == 443:
                        import ssl
                        ctx = ssl.create_default_context()
                        ctx.check_hostname = False
                        ctx.verify_mode = ssl.CERT_NONE
                        remote_socket = ctx.wrap_socket(remote_socket, server_hostname=hostname)

                    # Rewrite Request Headers
                    # 1. Change first line to GET /videoplayback...
                    # 2. Change Host header
                    new_request_lines = []
                    new_request_lines.append(f"GET {target_path} HTTP/1.1".encode())
                    
                    headers_part = request.split(b'\r\n\r\n')[0]
                    headers_lines = headers_part.split(b'\r\n')[1:] # Skip first line
                    
                    for hline in headers_lines:
                        if hline.lower().startswith(b'host:'):
                            new_request_lines.append(f"Host: {hostname}".encode())
                        else:
                            new_request_lines.append(hline)
                    
                    new_request_lines.append(b"") # Empty line
                    new_request_lines.append(b"") # End of headers
                    
                    remote_socket.send(b'\r\n'.join(new_request_lines))
                    
                    # Bridge connection
                    # Bridge connection with CORS injection
                    self.forward_response_with_cors(client_socket, remote_socket)
                    return

                except Exception as e:
                    log(f"❌ Relay Error: {e}")
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

    def forward_response_with_cors(self, client, remote):
        """
        Reads headers from remote, injects CORS, sends to client, then pipes body.
        """
        try:
            # Read header block
            header_data = b""
            while True:
                chunk = remote.recv(1)
                if not chunk:
                    break
                header_data += chunk
                if b"\r\n\r\n" in header_data:
                    break
            
            if not header_data:
                return

            # Split headers and body
            headers_part, body_start = header_data.split(b"\r\n\r\n", 1)
            lines = headers_part.split(b"\r\n")
            
            # Construct new headers
            new_lines = []
            status_line = lines[0]
            log(f"🌍 Upstream Status: {status_line.decode('utf-8', errors='ignore')}")
            
            new_lines.append(status_line)
            
            # Filter and add headers
            has_cors = False
            for line in lines[1:]:
                if line.lower().startswith(b"content-type:"):
                    log(f"📄 Upstream Content-Type: {line.decode('utf-8', errors='ignore')}")
                
                if line.lower().startswith(b"access-control-allow-origin"):
                    has_cors = True
                    new_lines.append(b"Access-Control-Allow-Origin: *") # Force wildcard
                else:
                    new_lines.append(line)
            
            if not has_cors:
                new_lines.append(b"Access-Control-Allow-Origin: *")
            
            # Reassemble headers
            new_header_block = b"\r\n".join(new_lines) + b"\r\n\r\n"
            
            # Send to client
            client.sendall(new_header_block)
            if body_start:
                client.sendall(body_start)
            
            # Pipe the rest of the body
            self.forward_data(client, remote)
            
        except Exception as e:
            log(f"Header injection error: {e}")
            pass
        finally:
            client.close()
            remote.close()

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

if __name__ == '__main__':
    proxy = ProxyServer(BIND_HOST, BIND_PORT)
    proxy.start()
