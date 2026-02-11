/**
 * DigitalOcean Serverless - Playground UI
 * Updated for serverless function endpoints
 */

// State
let currentMode = 'youtube';
let serverlessEndpoint = localStorage.getItem('serverlessEndpoint') || window.location.origin;

// DOM Elements
const queryInput = document.getElementById('search-query');
const resultsContainer = document.getElementById('results-container');
const consoleOutput = document.getElementById('console-output');
const playerContainer = document.getElementById('player-container');
const playerTitle = document.getElementById('player-title');
const playerArtist = document.getElementById('player-artist');
const playerThumb = document.getElementById('player-thumb');
const audioElement = document.getElementById('audio-element');

// Modes
function setMode(mode) {
    currentMode = mode;
    document.getElementById('btn-youtube').className = mode === 'youtube'
        ? 'flex-1 py-2 text-xs font-medium rounded-md bg-red-600 text-white shadow transition'
        : 'flex-1 py-2 text-xs font-medium rounded-md text-gray-400 hover:text-white transition';

    document.getElementById('btn-spotify').className = mode === 'spotify'
        ? 'flex-1 py-2 text-xs font-medium rounded-md bg-green-600 text-white shadow transition'
        : 'flex-1 py-2 text-xs font-medium rounded-md text-gray-400 hover:text-white transition';

    document.getElementById('spotify-type').disabled = mode !== 'spotify';
    log(`Switched to ${mode} mode`);
}

// Configuration Management
function setServerlessEndpoint() {
    const endpoint = prompt('Enter DigitalOcean Serverless Function Endpoint (URL)', serverlessEndpoint);
    if (endpoint) {
        serverlessEndpoint = endpoint;
        localStorage.setItem('serverlessEndpoint', endpoint);
        log(`✅ Endpoint set to: ${endpoint}`);
    }
}

// Log utility
function log(msg) {
    const time = new Date().toLocaleTimeString();
    consoleOutput.textContent += `[${time}] ${msg}\n`;
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function clearLog() {
    consoleOutput.textContent = 'Playground reinitialized. Ready for requests.';
}

// Format Duration
function formatDuration(sec_num) {
    if (!sec_num) return '--:--';
    let hours = Math.floor(sec_num / 3600);
    let minutes = Math.floor((sec_num - (hours * 3600)) / 60);
    let seconds = sec_num - (hours * 3600) - (minutes * 60);

    if (hours < 10) { hours = "0" + hours; }
    if (minutes < 10) { minutes = "0" + minutes; }
    if (seconds < 10) { seconds = "0" + seconds; }

    if (hours !== "00") return hours + ':' + minutes + ':' + seconds;
    return minutes + ':' + seconds;
}

// Extract Video ID from YouTube URL
function extractYoutubeId(url) {
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/,
        /^([a-zA-Z0-9_-]{11})$/ // Just the ID
    ];
    
    for (let pattern of patterns) {
        const match = url.match(pattern);
        if (match) return match[1];
    }
    return null;
}

// Core Search/Extract Logic
async function performSearch() {
    const query = queryInput.value.trim();
    if (!query) return alert('Please enter a query');

    const videoId = extractYoutubeId(query);
    
    if (currentMode === 'youtube' && videoId) {
        // If it's a YouTube ID or URL, use the direct extraction endpoint
        log(`📺 Extracting stream from YouTube video: ${videoId}`);
        await fetchAndPlayFromId(videoId);
    } else {
        // Alternative: use the generic search endpoint if available
        log(`🔍 Searching: ${query}`);
        log('Note: Direct search not available in serverless. Use YouTube video ID.');
    }
}

// Get Stream from URL Input (Direct Video ID/URL)
async function getStreamFromUrl() {
    const input = document.getElementById('direct-url').value.trim();
    if (!input) return;

    const videoId = extractYoutubeId(input);
    if (!videoId) {
        log('❌ Invalid YouTube URL or Video ID');
        return;
    }

    log(`🎬 Fetching stream for video: ${videoId}`);
    await fetchAndPlayFromId(videoId);
}

// Fetch Stream for Video ID
async function fetchAndPlayFromId(videoId) {
    if (!videoId) {
        log('Error: No video ID provided');
        return;
    }

    const apiUrl = `${serverlessEndpoint}/api/stream/${videoId}`;
    log(`📤 Calling: ${apiUrl}`);

    try {
        const response = await fetch(apiUrl);
        const data = await response.json();

        if (!response.ok) {
            log(`❌ Error (${response.status}): ${data.error || 'Unknown error'}`);
            return;
        }

        if (data.url) {
            playTrack({
                title: data.title || 'Unknown Title',
                artist: data.uploader || 'Unknown Artist',
                thumbnail: data.thumbnail,
                url: data.url,
                videoId: videoId,
                duration: data.duration,
                ext: data.ext || 'mp4'
            });
            log(`✅ Success! Playing: ${data.title}`);
        } else {
            log('❌ No stream URL in response');
        }
    } catch (e) {
        log(`❌ Fetch Error: ${e.message}`);
    }
}

// Fetch and Play Result Item
async function fetchAndPlay(item) {
    // If we already have a stream URL, use it
    if (item.url) {
        playTrack(item);
        return;
    }

    // Identify ID
    let videoId = item.videoId || item.id;
    if (!videoId) {
        log('Error: No video ID available');
        return;
    }

    // Get Stream URL from serverless function
    const streamApiUrl = `${serverlessEndpoint}/api/stream/${videoId}`;
    log(`🎥 Getting stream for ID: ${videoId}`);

    try {
        const res = await fetch(streamApiUrl);
        const data = await res.json();

        if (!res.ok) {
            log(`❌ Error: ${data.error}`);
            return;
        }

        if (data.url) {
            playTrack({
                title: item.title || data.title || 'Unknown',
                artist: item.artist || data.uploader || 'Unknown',
                thumbnail: item.thumbnail || data.thumbnail,
                url: data.url,
                videoId: videoId,
                duration: data.duration,
                ext: data.ext || 'mp4'
            });
            log(`✅ Playing: ${data.title}`);
        } else {
            log('❌ Failed to get stream URL');
        }
    } catch (e) {
        log(`❌ Stream Error: ${e.message}`);
    }
}

// Play Track
function playTrack(track) {
    playerContainer.classList.remove('hidden');

    playerTitle.textContent = track.title || 'Unknown Title';
    playerArtist.textContent = track.artist || 'Unknown Artist';
    playerThumb.src = track.thumbnail || '';

    log(`🎵 Setting Audio Source: ${track.url.substring(0, 60)}...`);
    audioElement.src = track.url;

    // Log media events
    audioElement.onerror = (e) => {
        const err = audioElement.error;
        log(`❌ Media Error: Code ${err?.code}, ${err?.message || 'Unable to load media'}`);
    };

    audioElement.onplay = () => {
        log(`▶️ Now Playing: ${track.title}`);
    };

    audioElement.onpause = () => {
        log(`⏸️ Paused: ${track.title}`);
    };

    audioElement.play().catch(e => log(`⚠️ Playback error: ${e.message}`));
}

// Render Results
function renderResults(results) {
    resultsContainer.innerHTML = '';
    const template = document.getElementById('result-template');

    if (!results || results.length === 0) {
        resultsContainer.innerHTML = '<div class="text-center text-gray-500 mt-10">No results found</div>';
        return;
    }

    results.forEach(item => {
        const clone = template.content.cloneNode(true);
        const root = clone.querySelector('div');

        clone.querySelector('.result-title').textContent = item.title || 'Untitled';
        clone.querySelector('.result-artist').textContent = item.uploader || item.artist || 'Unknown';
        clone.querySelector('.result-duration').textContent = formatDuration(item.duration) || '--:--';
        clone.querySelector('.result-thumb').src = item.thumbnail || '';

        // Play Button Click
        clone.querySelector('.play-btn').onclick = (e) => {
            e.stopPropagation();
            fetchAndPlay(item);
        };

        // Copy Link Button
        const copyBtn = clone.querySelector('.copy-btn');
        copyBtn.onclick = (e) => {
            e.stopPropagation();
            const id = item.videoId || item.id;
            if (!id) return;

            const streamApiUrl = `${serverlessEndpoint}/api/stream/${id}`;
            navigator.clipboard.writeText(streamApiUrl).then(() => {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i data-lucide="check" class="w-3 h-3 text-green-400"></i>';
                setTimeout(() => {
                    copyBtn.innerHTML = originalText;
                    lucide.createIcons();
                }, 2000);
                log(`✅ Copied API URL`);
            });
        };

        // JSON log click
        clone.querySelector('.json-btn').onclick = (e) => {
            e.stopPropagation();
            log(`Item: ${JSON.stringify(item, null, 2)}`);
        };

        resultsContainer.appendChild(clone);
    });

    lucide.createIcons();
}

// Health Check
async function checkHealth() {
    const healthUrl = `${serverlessEndpoint}/health`;
    try {
        const res = await fetch(healthUrl);
        const data = await res.json();
        if (res.ok) {
            log(`✅ Serverless function is healthy`);
            return true;
        }
    } catch (e) {
        log(`⚠️ Cannot reach serverless endpoint`);
        return false;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    log('🚀 DigitalOcean Serverless Playground initialized');
    log(`📍 Endpoint: ${serverlessEndpoint}`);
    checkHealth();
});
