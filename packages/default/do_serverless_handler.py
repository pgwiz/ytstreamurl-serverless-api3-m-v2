"""
DigitalOcean Serverless Functions Handler
Uses shared youtube_extractor module for proven extraction logic
Replaces previous serverless_handler.py with improved implementation
"""
import json
import os
import sys

# Add parent directory to path to import youtube_extractor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from youtube_extractor import YoutubeExtractor

# Initialize extractor with timeout suitable for serverless
extractor = YoutubeExtractor(
    cookies_file=os.environ.get('COOKIES_FILE'),
    timeout=int(os.environ.get('REQUEST_TIMEOUT', '45')),  # Serverless has tighter timeout
    log_func=lambda msg: print(f"[DO-Serverless] {msg}", flush=True)
)

def main(args):
    """
    DigitalOcean Serverless Functions entry point
    
    Args:
        args: Dictionary with 'action' and optional parameters
        
    Usage:
        {'action': 'search', 'query': 'baby', 'limit': 10}
        {'action': 'extract', 'video_id': 'dQw4w9WgXcQ'}
    """
    try:
        action = args.get('action', 'status').lower()
        
        if action == 'status':
            return handle_status()
        
        elif action == 'search':
            return handle_search(args)
        
        elif action == 'extract' or action == 'stream':
            return handle_extract(args)
        
        else:
            return {
                'error': f'Unknown action: {action}',
                'available_actions': ['status', 'search', 'extract'],
                'examples': {
                    'search': {'action': 'search', 'query': 'baby', 'limit': 10},
                    'extract': {'action': 'extract', 'video_id': 'dQw4w9WgXcQ'}
                }
            }
    
    except Exception as e:
        extractor.log(f'❌ Handler error: {e}')
        return {
            'error': str(e),
            'type': type(e).__name__
        }

def handle_status():
    """Return API status and capabilities"""
    import shutil
    
    node_available = bool(shutil.which('node'))
    cookies_path = extractor.get_cookie_file_path()
    
    return {
        'service': 'YouTube Extractor (DigitalOcean Serverless)',
        'status': 'ok',
        'version': '1.0.0',
        'capabilities': {
            'search': True,
            'extract': True,
            'node_js': node_available,
            'cookies': bool(cookies_path)
        },
        'limits': {
            'timeout_seconds': extractor.timeout,
            'max_search_results': 50
        }
    }

def handle_search(args):
    """Handle search action"""
    query = args.get('query') or args.get('q')
    if not query:
        return {'error': 'Missing query parameter'}
    
    limit = min(int(args.get('limit', 10)), 50)  # Cap at 50 for serverless
    
    extractor.log(f'🔍 Searching: {query} (limit: {limit})')
    results = extractor.search_youtube(query, limit=limit)
    
    return {
        'query': query,
        'results': results,
        'count': len(results),
        'success': len(results) > 0
    }

def handle_extract(args):
    """Handle extract/stream action"""
    video_id = args.get('video_id') or args.get('id')
    
    if not video_id or len(video_id) < 10:
        return {'error': 'Invalid or missing video_id parameter'}
    
    extractor.log(f'🎬 Extracting: {video_id}')
    result = extractor.extract_youtube_stream(video_id)
    
    if result:
        return {
            'video_id': video_id,
            'success': True,
            'data': result
        }
    else:
        return {
            'video_id': video_id,
            'success': False,
            'error': 'Failed to extract stream',
            'reason': 'Video may be unavailable, require authentication, or have no HTTP streams'
        }
