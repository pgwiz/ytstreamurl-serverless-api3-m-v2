"""
Shared YouTube extraction module for both serverless and web applications
Extracted from proven application.py logic for reusability across platforms
"""
import os
import sys
import json
import subprocess
import shutil
import tempfile
import logging
from functools import lru_cache

# --- Logging Setup ---
logger = logging.getLogger(__name__)

class YoutubeExtractor:
    """Shared YouTube extraction logic for serverless and web apps"""
    
    def __init__(self, cookies_file=None, timeout=60, log_func=None):
        """
        Initialize extractor
        
        Args:
            cookies_file: Path to cookies.txt file
            timeout: Subprocess timeout in seconds
            log_func: Optional custom logging function
        """
        self.cookies_file = cookies_file
        self.timeout = timeout
        self.log_func = log_func or self._default_log
        
        # Cookie caching
        self.cookie_manager = {
            'path': None,
            'loaded': False
        }
    
    def _default_log(self, msg):
        """Default logging function"""
        print(f"[YT] {msg}", flush=True)
    
    def log(self, msg):
        """Log message"""
        self.log_func(msg)
    
    def get_cookie_file_path(self):
        """Get or create cookie file path (reuse existing if available)."""
        if self.cookie_manager['loaded'] and self.cookie_manager['path'] and os.path.exists(self.cookie_manager['path']):
            return self.cookie_manager['path']
        
        # Check multiple possible locations
        possible_paths = [
            self.cookies_file,           # Explicitly provided
            '/app/cookies.txt',          # Docker image location
            '/tmp/cookies.txt',          # Docker compose mount
            'cookies.txt'                # Local directory
        ]
        
        # Return first existing path
        for path in possible_paths:
            if path and os.path.exists(path):
                try:
                    with open(path, "r", encoding='utf-8') as f:
                        cookie_data = f.read()
                    if cookie_data.strip():
                        temp_dir = tempfile.gettempdir()
                        cookie_path = os.path.join(temp_dir, "yt_cookies_runtime.txt")
                        
                        if not os.path.exists(cookie_path):
                            with open(cookie_path, "w", encoding='utf-8') as f:
                                f.write(cookie_data)
                        
                        self.cookie_manager['path'] = cookie_path
                        self.cookie_manager['loaded'] = True
                        self.log(f'🍪 Cookies loaded from: {path} ({len(cookie_data)} bytes)')
                        return cookie_path
                except Exception as e:
                    self.log(f'⚠️ Failed to load cookies from {path}: {e}')
                    continue
        
        # Try environment variable
        cookie_data = os.environ.get("YTDLP_COOKIES")
        if cookie_data:
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
        
        self.log('⚠️ No cookies found - authentication may be required')
        return None
    
    def search_youtube(self, query, limit=5):
        """Search YouTube using yt-dlp subprocess (proven method)"""
        try:
            # Use subprocess with sys.executable -m for reliable execution
            command = [
                sys.executable, "-m", "yt_dlp",
                f"ytsearch{limit}:{query}",
                "--dump-single-json",
                "--flat-playlist",
                "--no-cache-dir"
            ]
            
            # Add cookies if available
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
        """Extract YouTube stream URL using yt-dlp subprocess (proven method)"""
        try:
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Build yt-dlp command using sys.executable -m (most reliable)
            cmd = [
                sys.executable, "-m", "yt_dlp",
                youtube_url,
                '--no-cache-dir',
                '--no-check-certificate',
                '--dump-single-json',
                '--no-playlist',
                '-f', 'best[ext=mp4][protocol^=http]/best[protocol^=http]'
            ]
            
            # Add Node.js as JS runtime for signature solving if available
            node_path = shutil.which('node')
            if node_path:
                cmd.extend(['--js-runtimes', 'node'])
                self.log(f'📦 Using Node.js JS runtime from: {node_path}')
            else:
                # Fallback: try common paths
                for path in ['/usr/bin/node', '/usr/local/bin/node', '/bin/node']:
                    if os.path.exists(path):
                        cmd.extend(['--js-runtimes', 'node'])
                        self.log(f'📦 Using Node.js JS runtime from: {path}')
                        break
                else:
                    self.log('⚠️ Node.js not found - some videos may fail')
            
            # Add cookies if available
            cookie_path = self.get_cookie_file_path()
            if cookie_path:
                cmd.extend(['--cookies', cookie_path])
            
            self.log(f'🎬 Extracting video: {video_id}')
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            
            if result.returncode != 0:
                self.log(f'❌ yt-dlp failed: {result.stderr[:300]}')
                return None
            
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                self.log(f'❌ JSON parse error: {e}')
                self.log(f'📝 stdout: {result.stdout[:200]}')
                return None
            
            stream_url = data.get('url')
            if not stream_url:
                self.log(f'❌ No stream URL found in response')
                self.log(f'📝 Response keys: {list(data.keys())}')
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
    
    def extract_media_info(self, youtube_url: str):
        """Extract media info from URL (playlist or single video)"""
        try:
            command = [
                sys.executable, "-m", "yt_dlp",
                youtube_url,
                '--dump-single-json',
                '--no-cache-dir'
            ]
            
            cookie_path = self.get_cookie_file_path()
            if cookie_path:
                command.extend(['--cookies', cookie_path])
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout)
            
            if result.returncode != 0:
                self.log(f'❌ Failed to extract: {result.stderr[:200]}')
                return None
            
            return json.loads(result.stdout)
        except Exception as e:
            self.log(f'Extract media info error: {e}')
            return None


# Convenience functions for backward compatibility
_default_extractor = None

def get_default_extractor():
    """Get or create default extractor instance"""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = YoutubeExtractor()
    return _default_extractor

def search_youtube(query, limit=5):
    """Search YouTube (uses default extractor)"""
    return get_default_extractor().search_youtube(query, limit)

def extract_youtube_stream(video_id):
    """Extract stream (uses default extractor)"""
    return get_default_extractor().extract_youtube_stream(video_id)

def extract_media_info(youtube_url):
    """Extract media info (uses default extractor)"""
    return get_default_extractor().extract_media_info(youtube_url)
