import os
from flask import Flask, request, Response
import requests
from http.server import BaseHTTPRequestHandler

# Initialize Flask app
app = Flask(__name__)

# Configurable domain for homepage logic
PROXY_DOMAIN = os.environ.get('PROXY_DOMAIN', 'prx.pgwiz.cloud')

@app.route('/health')
def health():
    return "Proxy Server is Alive"

@app.route('/', defaults={'path': ''}, methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
@app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
def proxy(path):
    """
    Standard HTTP Proxy forwarding with Homepage support.
    """
    # Homepage Logic: If the request is specifically for this server
    if request.host == PROXY_DOMAIN and not path:
        return "<h1>Hello John Doe</h1>"
    
    try:
        # Exclude host header to avoid conflicts
        headers = {key: value for (key, value) in request.headers if key != 'Host'}
        
        resp = requests.request(
            method=request.method,
            url=request.url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30
        )
        
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        
        response = Response(resp.content, resp.status_code, headers)
        return response
        
    except Exception as e:
        return Response(f"Proxy Error: {str(e)}", 500)


class handler(BaseHTTPRequestHandler):
    """
    Vercel Serverless Function handler that wraps the Flask application.
    """
    
    def do_GET(self):
        self._handle_request()
    
    def do_POST(self):
        self._handle_request()
    
    def do_PUT(self):
        self._handle_request()
    
    def do_DELETE(self):
        self._handle_request()
    
    def do_HEAD(self):
        self._handle_request()
    
    def do_OPTIONS(self):
        self._handle_request()
    
    def _handle_request(self):
        """Handle the request using Flask's test client."""
        # Build the Flask request context
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''
        
        # Convert headers to dict
        headers = {}
        for key, value in self.headers.items():
            headers[key] = value
        
        # Use Flask test client to handle the request
        with app.test_client() as client:
            # Construct the request
            response = client.open(
                self.path,
                method=self.command,
                headers=headers,
                data=body
            )
            
            # Send response back
            self.send_response(response.status_code)
            
            # Send headers
            for key, value in response.headers:
                if key.lower() not in ['content-length', 'transfer-encoding']:
                    self.send_header(key, value)
            
            response_data = response.get_data()
            self.send_header('Content-Length', len(response_data))
            self.end_headers()
            
            # Send body
            self.wfile.write(response_data)
