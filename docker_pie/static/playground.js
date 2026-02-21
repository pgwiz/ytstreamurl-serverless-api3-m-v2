// API Playground JavaScript

const API_BASE = window.location.origin;

// Load API status on page load
document.addEventListener('DOMContentLoaded', function() {
    loadStatus();
    loadStoredValues();
});

// Base64 encoding utility
function encodeBase64(str) {
    return btoa(unescape(encodeURIComponent(str)));
}

function loadStatus() {
    fetch(`${API_BASE}/api/status`)
        .then(res => res.json())
        .then(data => {
            const statusInfo = document.getElementById('statusInfo');
            statusInfo.innerHTML = `
                <div class="text-center">
                    <p class="text-gray-500 text-sm">Service</p>
                    <p class="text-white font-bold">${data.service}</p>
                </div>
                <div class="text-center">
                    <p class="text-gray-500 text-sm">Version</p>
                    <p class="text-white font-bold">${data.version}</p>
                </div>
                <div class="text-center">
                    <p class="text-gray-500 text-sm">Node.js</p>
                    <p class="text-white font-bold">${data.node_js ? '✅ Available' : '❌ Missing'}</p>
                </div>
                <div class="text-center">
                    <p class="text-gray-500 text-sm">Cookies</p>
                    <p class="text-white font-bold">${data.cookies ? '✅ Found' : '❌ Missing'}</p>
                </div>
            `;
        })
        .catch(err => console.error('Status error:', err));
}

function searchYouTube() {
    const query = document.getElementById('searchQuery').value.trim();
    if (!query) {
        alert('Please enter a search query');
        return;
    }

    localStorage.setItem('lastSearchQuery', query);
    
    const resultsDiv = document.getElementById('searchResults');
    resultsDiv.innerHTML = '<p class="text-gray-400">🔄 Searching...</p>';

    fetch(`${API_BASE}/api/search/youtube?q=${encodeURIComponent(query)}&limit=10`)
        .then(res => res.json())
        .then(data => {
            if (data.results && data.results.length > 0) {
                resultsDiv.innerHTML = data.results.map((video, idx) => `
                    <div class="cursor-pointer p-3 bg-gray-700 hover:bg-gray-600 rounded transition" 
                         onclick="selectVideo('${video.id}', '${video.title}')">
                        <div class="flex gap-3">
                            ${video.thumbnail ? `<img src="${video.thumbnail}" alt="${video.title}" class="w-16 h-16 rounded object-cover">` : '<div class="w-16 h-16 bg-gray-600 rounded"></div>'}
                            <div class="flex-1">
                                <p class="font-bold text-sm line-clamp-2">${video.title}</p>
                                <p class="text-xs text-gray-400 mt-1">📺 ${video.uploader}</p>
                                <p class="text-xs text-gray-500">⏱️ ${formatDuration(video.duration)}</p>
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                resultsDiv.innerHTML = '<p class="text-gray-400">No results found</p>';
            }
        })
        .catch(err => {
            console.error('Search error:', err);
            resultsDiv.innerHTML = '<p class="text-red-400">Search failed</p>';
        });
}

function selectVideo(videoId, title) {
    document.getElementById('videoId').value = videoId;
    localStorage.setItem('lastVideoId', videoId);
    extractStream();
}

function extractStream() {
    const videoId = document.getElementById('videoId').value.trim();
    if (!videoId || videoId.length < 10) {
        alert('Please enter a valid video ID (at least 11 characters)');
        return;
    }

    localStorage.setItem('lastVideoId', videoId);

    const resultDiv = document.getElementById('streamResult');
    const infoDiv = document.getElementById('streamInfo');
    
    resultDiv.classList.remove('hidden');
    infoDiv.innerHTML = '<p class="text-gray-400">⏳ Extracting stream...</p>';

    fetch(`${API_BASE}/api/stream/${videoId}`)
        .then(res => res.json())
        .then(data => {
            if (data.title) {
                // Success
                const streamUrl = data.url;
                const proxyUrl = `${API_BASE}/stream/play?url=${encodeBase64(streamUrl)}`;
                
                // Store current video info for download
                window.currentVideoInfo = {
                    videoId: videoId,
                    title: data.title,
                    url: streamUrl,
                    proxyUrl: proxyUrl
                };
                
                infoDiv.innerHTML = `
                    <div class="space-y-3">
                        <h3 class="text-lg font-bold text-green-400">✅ Stream Extracted!</h3>
                        <div class="space-y-2 text-sm">
                            <p><strong>Title:</strong> ${escapeHtml(data.title)}</p>
                            <p><strong>Uploader:</strong> ${escapeHtml(data.uploader)}</p>
                            <p><strong>Duration:</strong> ${formatDuration(data.duration)}</p>
                            <p><strong>Format:</strong> ${data.ext.toUpperCase()}</p>
                        </div>
                        <div class="mt-4 space-y-2">
                            <p class="text-xs text-gray-400">🔗 Proxy Streaming URL (Share this):</p>
                            <div class="bg-gray-900 p-3 rounded border border-gray-700">
                                <p class="text-xs break-all font-mono text-green-300">${proxyUrl}</p>
                            </div>
                            <button onclick="copyProxyUrl()" class="w-full bg-green-600 hover:bg-green-700 text-white py-2 px-3 rounded text-xs font-bold transition">
                                📋 Copy Proxy URL
                            </button>
                        </div>
                        <div class="mt-3 space-y-2 pt-3 border-t border-gray-700">
                            <p class="text-xs text-gray-400">🎬 Playback Options:</p>
                            <div class="flex gap-2">
                                <button onclick="playStreamProxy()" class="flex-1 bg-green-600 hover:bg-green-700 text-white py-1 px-2 rounded text-xs font-bold transition">
                                    ▶️ Play
                                </button>
                                <button onclick="downloadVideo()" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-1 px-2 rounded text-xs font-bold transition">
                                    ⬇️ Download
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            } else if (data.error) {
                // Error
                infoDiv.innerHTML = `
                    <div class="space-y-3">
                        <h3 class="text-lg font-bold text-red-400">❌ Error</h3>
                        <p class="text-sm text-gray-300">${escapeHtml(data.reason || data.error)}</p>
                    </div>
                `;
            }
        })
        .catch(err => {
            console.error('Stream error:', err);
            infoDiv.innerHTML = '<p class="text-red-400">Failed to extract stream. Check console for details.</p>';
        });
}

function copyStreamUrl(url) {
    navigator.clipboard.writeText(url).then(() => {
        alert('✅ URL copied to clipboard!');
    }).catch(() => {
        alert('❌ Failed to copy URL');
    });
}

function playStream(url, title) {
    // Open in a new popup with video player
    const playerHtml = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>${title}</title>
            <style>
                body { margin: 0; background: #000; }
                video { width: 100%; height: 100vh; object-fit: contain; }
            </style>
        </head>
        <body>
            <video controls autoplay>
                <source src="${url}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </body>
        </html>
    `;
    
    const blob = new Blob([playerHtml], { type: 'text/html' });
    const playerUrl = URL.createObjectURL(blob);
    window.open(playerUrl, 'player', 'width=1000,height=600');
}

function playStreamProxy() {
    if (!window.currentVideoInfo) {
        alert('No video selected');
        return;
    }
    
    const { proxyUrl, title } = window.currentVideoInfo;
    
    // Play through server proxy
    const playerPanel = document.getElementById('playerPanel');
    const videoSource = document.getElementById('videoSource');
    const videoPlayer = document.getElementById('videoPlayer');
    
    playerPanel.classList.remove('hidden');
    videoSource.src = proxyUrl;
    videoPlayer.load();
    videoPlayer.play();
}

function downloadVideo() {
    if (!window.currentVideoInfo) {
        alert('No video selected');
        return;
    }
    
    const { title, proxyUrl } = window.currentVideoInfo;
    const filename = `${title.replace(/[^\w\s-]/g, '')}.mp4`;
    
    // Use proxy URL for download (goes through server)
    const downloadUrl = proxyUrl || window.currentVideoInfo.url;
    
    // Create a hidden anchor element and trigger download
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    alert(`⬇️ Download started for: ${title}\n📡 Using proxy URL for download`);
}

function closePlayer() {
    document.getElementById('playerPanel').classList.add('hidden');
    document.getElementById('videoPlayer').pause();
}

function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function loadStoredValues() {
    const lastQuery = localStorage.getItem('lastSearchQuery');
    if (lastQuery) {
        document.getElementById('searchQuery').value = lastQuery;
    }
    
    const lastVideoId = localStorage.getItem('lastVideoId');
    if (lastVideoId) {
        document.getElementById('videoId').value = lastVideoId;
    }
}

// Allow Enter key to trigger search/extract
document.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        if (document.activeElement.id === 'searchQuery') {
            searchYouTube();
        } else if (document.activeElement.id === 'videoId') {
            extractStream();
        }
    }
});
