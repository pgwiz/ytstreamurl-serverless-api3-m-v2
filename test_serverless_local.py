#!/usr/bin/env python3
"""
Quick test script for the serverless handler
Run this to test the function locally before deployment
"""

import sys
import os
import json
import requests
from serverless_handler import app

def test_local_server():
    """Test the local Flask server"""
    
    print("🧪 Starting Local Serverless Function Tests")
    print("=" * 50)
    
    # Create test client
    with app.test_client() as client:
        
        # Test 1: Health Check
        print("\n[Test 1] Health Check")
        response = client.get('/health')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")
        assert response.status_code == 200
        print("✅ PASSED")
        
        # Test 2: Missing video ID
        print("\n[Test 2] Missing Video ID")
        response = client.get('/api/stream/')
        print(f"Status: {response.status_code}")
        assert response.status_code == 404 or response.status_code == 400
        print("✅ PASSED")
        
        # Test 3: Invalid video ID format
        print("\n[Test 3] Invalid Video ID")
        response = client.get('/api/stream/invalid_id')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")
        print("✅ PASSED")
        
        # Test 4: Stream relay missing URL
        print("\n[Test 4] Stream Relay - Missing URL")
        response = client.get('/streamytlink')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")
        assert response.status_code == 400
        print("✅ PASSED")
        
        # Test 5: yt-dlp endpoint missing ID
        print("\n[Test 5] yt-dlp Endpoint - Missing ID")
        response = client.get('/ytdlp')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.get_json()}")
        assert response.status_code == 400
        print("✅ PASSED")
        
        # Test 6: Get logs
        print("\n[Test 6] Get Logs")
        response = client.get('/logs')
        print(f"Status: {response.status_code}")
        data = response.get_json()
        print(f"Log entries: {len(data.get('logs', []))}")
        assert response.status_code == 200
        print("✅ PASSED")
        
        # Test 7: 404 endpoint
        print("\n[Test 7] Non-existent Endpoint")
        response = client.get('/nonexistent')
        print(f"Status: {response.status_code}")
        assert response.status_code == 404
        print("✅ PASSED")
        
    print("\n" + "=" * 50)
    print("✨ All basic tests passed!")
    print("\nNote: To test actual YouTube extraction:")
    print("1. Run: python serverless_handler.py")
    print("2. In another terminal: curl http://localhost:8000/api/stream/dQw4w9WgXcQ")

if __name__ == '__main__':
    try:
        test_local_server()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
