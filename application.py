from flask import Flask, request, Response
import requests
import sys

# Initialize Flask app
# The WSGI loader looks for 'app' or 'application' in this file
app = Flask(__name__)

@app.route('/health')
def health():
    return "Proxy Server is Alive"

@app.route('/', defaults={'path': ''}, methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
@app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"])
def proxy(path):
    """
    Standard HTTP Proxy forwarding with Homepage support.
    """
    # 1. Homepage Logic: If the request is specifically for this server (prx.pgwiz.cloud)
    # Generic check: if path is empty and we are not proxying (based on logic or headers)
    # The safest way in a WSGI env is checking if the Host header matches your domain.
    # Adjust 'prx.pgwiz.cloud' if your domain logic differs.
    if request.host == 'prx.pgwiz.cloud' and not path:
        return "<h1>Hello John Doe</h1>"
        
    target_url = request.url
    
    # If the client is just hitting the root or a path, we might need to assume a target 
    # OR the client is treating this as a standard HTTP proxy.
    # But browsers/undici sending to a PROXY usually send the full URL in the request line.
    # Flask puts that in `request.url`.
    
    # Basic logic: Forward request to the actual generic destination
    # This might fail for "CONNECT" requests (HTTPS).
    
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6178)
