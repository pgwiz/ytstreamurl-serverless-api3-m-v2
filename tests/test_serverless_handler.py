"""
Basic tests for the serverless handler
"""

import pytest
import json
from serverless_handler import app, extract_youtube_stream

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_stream_relay_missing_url(client):
    """Test stream relay with missing URL parameter"""
    response = client.get('/streamytlink')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'Missing' in data['error']

def test_ytdlp_missing_id(client):
    """Test yt-dlp endpoint with missing ID"""
    response = client.get('/ytdlp')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'Missing' in data['error']

def test_logs_endpoint(client):
    """Test logs endpoint"""
    response = client.get('/logs')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'logs' in data
    assert isinstance(data['logs'], list)

def test_not_found(client):
    """Test 404 error handling"""
    response = client.get('/nonexistent')
    assert response.status_code == 404

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
