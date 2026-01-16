// State
let currentMode = 'youtube';

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

// Log utility
function log(msg) {
    const time = new Date().toLocaleTimeString();
    consoleOutput.textContent += `[${time}] ${msg}\n`;
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function clearLog() {
    consoleOutput.textContent = '';
}

// Format Duration
function formatDuration(sec_num) {
    let hours = Math.floor(sec_num / 3600);
    let minutes = Math.floor((sec_num - (hours * 3600)) / 60);
    let seconds = sec_num - (hours * 3600) - (minutes * 60);

    if (hours < 10) { hours = "0" + hours; }
    if (minutes < 10) { minutes = "0" + minutes; }
    if (seconds < 10) { seconds = "0" + seconds; }

    if (hours !== "00") return hours + ':' + minutes + ':' + seconds;
    return minutes + ':' + seconds;
}

// Core Search Logic
async function performSearch() {
    const query = queryInput.value.trim();
    if (!query) return alert('Please enter a query');

    const limit = document.getElementById('search-limit').value || 10;
    const spotifyType = document.getElementById('spotify-type').value;

    let url = '';
    if (currentMode === 'youtube') {
        url = `/api/search/youtube?query=${encodeURIComponent(query)}&limit=${limit}`;
    } else {
        url = `/api/search/spotify?query=${encodeURIComponent(query)}&type=${spotifyType}&limit=${limit}`;
    }

    log(`Fetching: ${url}`);

    try {
        const response = await fetch(url);
        const data = await response.json();
        log(`Response: ${JSON.stringify(data, null, 2)}`); // Full log

        renderResults(data.results || []);
    } catch (error) {
        log(`Error: ${error.message}`);
    }
}

// Get Stream from URL Input
async function getStreamFromUrl() {
    const url = document.getElementById('direct-url').value.trim();
    if (!url) return;

    const apiUrl = `/get?ytl=${encodeURIComponent(url)}`;
    log(`Fetching stream: ${apiUrl}`);

    try {
        const response = await fetch(apiUrl);
        const data = await response.json();

        if (data.tracks && data.tracks.length > 0) {
            const track = data.tracks[0];
            playTrack({
                title: track.title,
                artist: track.uploader,
                thumbnail: track.thumbnail,
                url: track.url,
                videoId: track.videoId
            });
            log(`Playing direct stream: ${track.title}`);
        } else {
            log('No streamable tracks found');
        }
    } catch (e) {
        log(`Error: ${e.message}`);
    }
}

// Fetch Stream for Result Item
async function fetchAndPlay(item) {
    // If we already have a stream URL (rare for search results usually), use it
    if (item.streamUrl) {
        playTrack(item);
        return;
    }

    // Identify ID
    let videoId = item.videoId || item.id;
    if (!videoId) {
        log('Error: No video ID available');
        return;
    }

    // If Spotify result, we can't play directly without resolving to YouTube first.
    // For this playground, let's assume we implement a basic fallback or just alert.
    if (currentMode === 'spotify') {
        // In a real app, you'd search YouTube with "Artist - Track" here.
        log(`Spotify Playback: Resolving "${item.name} - ${item.artist}" on YouTube...`);
        // Basic resolution attempt
        const searchQ = `${item.name} ${item.artist}`;
        const searchUrl = `/api/search/youtube?query=${encodeURIComponent(searchQ)}&limit=1`;

        try {
            const res = await fetch(searchUrl);
            const data = await res.json();
            if (data.results && data.results.length > 0) {
                videoId = data.results[0].videoId;
                log(`Resolved to YouTube ID: ${videoId}`);
            } else {
                log('Could not find match on YouTube');
                return;
            }
        } catch (e) {
            log(`Resolution Error: ${e.message}`);
            return;
        }
    }

    // Get Stream URL
    const streamApiUrl = `/stream/${videoId}`;
    log(`Getting stream for ID ${videoId}...`);

    try {
        const res = await fetch(streamApiUrl);
        const data = await res.json();

        if (data.streamUrl) {
            playTrack({
                title: item.title || item.name, // Handle difference in keys
                artist: item.artist || item.uploader,
                thumbnail: item.thumbnail,
                url: data.streamUrl,
                videoId: videoId
            });
            log(`Success! Playing: ${item.name || item.title}`);
        } else {
            log('Failed to get stream URL');
        }
    } catch (e) {
        log(`Stream Error: ${e.message}`);
    }
}

function playTrack(track) {
    playerContainer.classList.remove('hidden');

    playerTitle.textContent = track.title || 'Unknown Title';
    playerArtist.textContent = track.artist || 'Unknown Artist';
    playerThumb.src = track.thumbnail || '';

    audioElement.src = track.url;
    audioElement.play().catch(e => log(`Playback failed: ${e.message}`));
}

function renderResults(results) {
    resultsContainer.innerHTML = '';
    const template = document.getElementById('result-template');

    if (results.length === 0) {
        resultsContainer.innerHTML = '<div class="text-center text-gray-500 mt-10">No results found</div>';
        return;
    }

    results.forEach(item => {
        const clone = template.content.cloneNode(true);
        const root = clone.querySelector('div');

        clone.querySelector('.result-title').textContent = item.name || item.title || 'Untitled';
        clone.querySelector('.result-artist').textContent = item.artist || item.uploader || 'Unknown';
        clone.querySelector('.result-duration').textContent = item.duration_string || item.duration || '';
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

            const fullUrl = `${window.location.origin}/stream/${id}`;
            navigator.clipboard.writeText(fullUrl).then(() => {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i data-lucide="check" class="w-3 h-3 text-green-400"></i>';
                setTimeout(() => {
                    copyBtn.innerHTML = originalText;
                    lucide.createIcons();
                }, 2000);
                log(`Copied URL: ${fullUrl}`);
            });
        };

        // JSON log click
        clone.querySelector('.json-btn').onclick = (e) => {
            e.stopPropagation();
            log(`Item Data: ${JSON.stringify(item, null, 2)}`);
        };

        resultsContainer.appendChild(clone);
    });

    lucide.createIcons();
}

// Initial Log
log('Playground initialized. Ready for requests.');
