import json
import os
from datetime import datetime

# Minimal handler following DigitalOcean Functions Python runtime guide
# Exposes `main(event, context)` which receives event dict and context object

LOG_DIR = os.environ.get('LOG_DIR', '/tmp/proxyLogs')
os.makedirs(LOG_DIR, exist_ok=True)

def _log(msg):
    ts = datetime.utcnow().isoformat() + 'Z'
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
        with open(os.path.join(LOG_DIR, 'startup.log'), 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

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

    # Unknown path
    _log(f'unknown path: {path}')
    return {"body": {"error": "Not found", "path": path}, "statusCode": 404}
