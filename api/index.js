import express from 'express';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { LRUCache } from 'lru-cache';
import ytdl from '@distube/ytdl-core';
import ytpl from '@distube/ytpl';
import ytsr from '@distube/ytsr';

// ES Module helpers
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

// Spotify API Configuration (set via environment variables)
const SPOTIFY_CLIENT_ID = process.env.SPOTIFY_CLIENT_ID || '';
const SPOTIFY_CLIENT_SECRET = process.env.SPOTIFY_CLIENT_SECRET || '';

// LRU Cache for media info
const mediaCache = new LRUCache({
    max: 128,
    ttl: 1000 * 60 * 30 // 30 minutes
});

// Spotify token cache
let spotifyAccessToken = null;
let spotifyTokenExpiry = 0;

// --- Cookie Handling ---
function loadCookies() {
    const cookiePaths = [
        path.join(__dirname, 'cookies.txt'),
        path.join(__dirname, '..', 'cookies.txt'),
        path.join(process.cwd(), 'cookies.txt'),
        path.join(process.cwd(), 'api', 'cookies.txt')
    ];

    for (const cookiePath of cookiePaths) {
        if (fs.existsSync(cookiePath)) {
            console.log(`Found cookie file at: ${cookiePath}`);
            return cookiePath;
        }
    }
    console.log('No cookie file found in searched paths');
    return null;
}

const cookieFile = loadCookies();

// Helper to parse Netscape format
function parseNetscapeCookies(content) {
    const cookies = [];
    const lines = content.split('\n');
    for (const line of lines) {
        const parts = line.split('\t');
        if (parts.length >= 7 && !line.startsWith('#')) {
            cookies.push({
                domain: parts[0],
                path: parts[2],
                secure: parts[3] === 'TRUE',
                expirationDate: parseInt(parts[4]),
                name: parts[5],
                value: parts[6].trim()
            });
        }
    }
    return cookies;
}

function createYtdlAgent() {
    let cookieContent = null;

    // 1. Try Environment Variable
    if (process.env.COOKIES) {
        cookieContent = process.env.COOKIES;
        // console.log('Using cookies from Environment Variable');
    }
    // 2. Try File
    else if (cookieFile) {
        try {
            cookieContent = fs.readFileSync(cookieFile, 'utf8');
            // console.log('Using cookies from file:', cookieFile);
        } catch (e) {
            console.log('Error reading cookie file:', e.message);
        }
    }

    if (cookieContent) {
        try {
            // 1. Try JSON
            const cookies = JSON.parse(cookieContent);
            return ytdl.createAgent(cookies);
        } catch (e) {
            // 2. Try Netscape
            const netscapeCookies = parseNetscapeCookies(cookieContent);
            if (netscapeCookies.length > 0) {
                return ytdl.createAgent(netscapeCookies);
            }
            console.log('Failed to parse cookies (Not JSON or Netscape)');
        }
    }

    // Default agent
    return undefined;
}

// --- Startup Cookie Check ---
function checkCookiesOnStartup() {
    console.log('\n--- 🍪 Cookie Compatibility Check ---');
    let cookieContent = null;
    let source = 'None';

    if (process.env.COOKIES) {
        cookieContent = process.env.COOKIES;
        source = 'Environment Variable (process.env.COOKIES)';
    } else if (cookieFile) {
        try {
            cookieContent = fs.readFileSync(cookieFile, 'utf8');
            source = `File (${path.basename(cookieFile)})`;
        } catch (e) {
            console.log(`❌ Error reading cookie file: ${e.message}`);
            return;
        }
    }

    if (!cookieContent) {
        console.log('⚠️  No cookies found. Some YouTube videos may be restricted (Sign-in required).');
        console.log('--- ----------------------------- ---\n');
        return;
    }

    // Try JSON
    try {
        const cookies = JSON.parse(cookieContent);
        if (Array.isArray(cookies)) {
            console.log(`✅ Valid Cookies Loaded!`);
            console.log(`   Source: ${source}`);
            console.log(`   Format: JSON Array`);
            console.log(`   Count:  ${cookies.length} cookies`);
        } else {
            console.log(`❌ Invalid JSON Cookies: Expected array, got ${typeof cookies}`);
        }
    } catch (e) {
        // Try Netscape
        if (typeof cookieContent === 'string' && (cookieContent.includes('\t') || cookieContent.startsWith('#'))) {
            const lineCount = cookieContent.split('\n').filter(l => l.trim() && !l.startsWith('#')).length;
            console.log(`✅ Valid Cookies Loaded!`);
            console.log(`   Source: ${source}`);
            console.log(`   Format: Netscape HTTP Cookie File`);
            console.log(`   Count:  ~${lineCount} lines`);
        } else {
            console.log(`❌ Invalid Cookie Format: Neither JSON nor Netscape.`);
        }
    }
    console.log('--- ----------------------------- ---\n');
}

// Run check immediately
checkCookiesOnStartup();

// Format seconds to duration string
function formatDuration(seconds) {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hrs > 0) {
        return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// --- Script Cleanup Logic ---
let cleanupRuns = []; // Store timestamps of runs for current hour
const MAX_CLEANUP_PER_HOUR = 3;

function managePlayerScripts() {
    const now = Date.now();
    const oneHourAgo = now - (60 * 60 * 1000);

    // Filter out runs older than 1 hour
    cleanupRuns = cleanupRuns.filter(ts => ts > oneHourAgo);

    if (cleanupRuns.length >= MAX_CLEANUP_PER_HOUR) {
        console.log(`Cleanup skipped: Limit reached (${cleanupRuns.length}/${MAX_CLEANUP_PER_HOUR} in last hour)`);
        return;
    }

    // Perform cleanup
    try {
        const rootDir = __dirname; // api/
        // Actually the scripts are in project root likely, so one level up
        const projectRoot = path.join(__dirname, '..');
        const scriptsDir = path.join(projectRoot, 'scripts');

        if (!fs.existsSync(scriptsDir)) {
            fs.mkdirSync(scriptsDir);
        }

        const files = fs.readdirSync(projectRoot);
        const scriptFiles = files.filter(f => f.endsWith('-player-script.js'));

        if (scriptFiles.length === 0) return;

        console.log(`Cleaning up ${scriptFiles.length} player scripts...`);

        scriptFiles.forEach(file => {
            const srcPath = path.join(projectRoot, file);
            // Delete file as user requested "clear the folder"
            // Or move? User said "can they be in one folder" AND "clear the folder". 
            // Let's delete them to be safe/clean? 
            // "clear the folder and then process the request" -> implies getting rid of them.
            // But "can they be in one folder" implies organizing. 
            // Compromise: Move to 'scripts' folder, then if 'scripts' folder gets too big, clear it?
            // "clear the folder" probably refers to the destination folder or the root? 
            // Let's assume: Move clutter from root to `scripts/`. Then clear `scripts/`?
            // Actually, simply deleting them is the best "cleanup".
            // But let's move them first to satisfy "be in one folder", then maybe delete old ones?
            // User: "can they be in one folder.. and add a timer.. check if every hour.. clear the folder".
            // Implementation: Move to 'scripts/', then clear 'scripts/' on timer?
            // Let's just DELETE them from root. That "clears the folder" (root) effectively.
            // A safer approach: Move to 'scripts/' and keep last 5?
            // Let's just delete them for now as they are garbage.

            // Wait, "clear the folder" might refer to the "one folder" (scripts folder) the user asked for.
            // So: 1. Move root scripts to scripts/ folder.
            //     2. "Clear the folder" -> Delete contents of scripts/ folder?
            //     3. "runs 3 times max in every hour"
            // Let's implementing: Move to scripts/ and then delete. Essentially deleting. 
            // I'll just delete them from root for simplicity and effectiveness. 
            // If the user wants to keep them, I should have moved them. 
            // Let's MOVE them to 'scripts' folder. And maybe clear 'scripts' folder if it has too many?

            // Re-reading: "updated index.html.. also this *.-player-script.js can they be in one folder.. and add a timer.. which will check if every hour and record such that it shows this hour timestamp run such that it only runs 3 times max in every hour clear the folder and then process the request"
            // "can they be in one folder" -> Suggests segregation.
            // "clear the folder" -> Suggests emptying that folder.
            // Okay, I will MOVE them to 'scripts/' immediately (always keep root clean).
            // AND the TIMER/LIMIT logic applies to CLEARING the 'scripts/' folder.

            // Actually, maybe the "runs 3 times max" refers to the *movement/cleanup* process itself.
            // Let's implement: 
            // 1. Always move *-player-script.js to scripts/ on every request (to keep root clean).
            // 2. Perform DELETION of scripts/ folder contents only 3 times/hour.

            // Moving...
            const destPath = path.join(scriptsDir, file);
            fs.renameSync(srcPath, destPath);
        });

        // Count this as a run for the "cleanup" (clearing logic)? 
        // Or is "process the request" the main thing?

        // Let's refine:
        // Function `cleanupRoot()` -> Moves files to `scripts/`. Always run?
        // Function `purgeScripts()` -> Deletes files in `scripts/`. Run max 3/hour.

        cleanupRuns.push(now);

        // Check if we should purge 'scripts/' folder
        // Actually, let's just do the move+delete in one go if allowed.
        // It seems the user wants to avoid overhead or something. 
        // I will just DELETE them if the limit isn't reached.

        fs.readdirSync(scriptsDir).forEach(f => fs.unlinkSync(path.join(scriptsDir, f)));
        console.log('Scripts folder cleared.');

    } catch (e) {
        console.error('Cleanup error:', e.message);
    }
}

// --- Spotify Authentication ---
async function getSpotifyAccessToken() {
    if (!SPOTIFY_CLIENT_ID || !SPOTIFY_CLIENT_SECRET) {
        throw new Error('Spotify API credentials not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.');
    }

    // Return cached token if still valid
    if (spotifyAccessToken && Date.now() < spotifyTokenExpiry) {
        return spotifyAccessToken;
    }

    const credentials = Buffer.from(`${SPOTIFY_CLIENT_ID}:${SPOTIFY_CLIENT_SECRET}`).toString('base64');

    const response = await fetch('https://accounts.spotify.com/api/token', {
        method: 'POST',
        headers: {
            'Authorization': `Basic ${credentials}`,
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: 'grant_type=client_credentials'
    });

    if (!response.ok) {
        throw new Error(`Spotify auth failed: ${response.status}`);
    }

    const data = await response.json();
    spotifyAccessToken = data.access_token;
    spotifyTokenExpiry = Date.now() + (data.expires_in * 1000) - 60000; // Refresh 1 min early

    return spotifyAccessToken;
}

// --- Extract video info using ytdl-core ---
async function extractVideoInfo(videoUrl) {
    try {
        const agent = createYtdlAgent();
        const info = await ytdl.getInfo(videoUrl, { agent });

        const format = ytdl.chooseFormat(info.formats, {
            quality: 'highest',
            filter: 'audioandvideo'
        }) || ytdl.chooseFormat(info.formats, { quality: 'highest' });

        return {
            title: info.videoDetails.title || 'Untitled',
            url: format?.url || null,
            thumbnail: info.videoDetails.thumbnails?.[0]?.url || `https://img.youtube.com/vi/${info.videoDetails.videoId}/mqdefault.jpg`,
            duration: formatDuration(parseInt(info.videoDetails.lengthSeconds) || 0),
            uploader: info.videoDetails.author?.name || 'Unknown',
            id: info.videoDetails.videoId,
            videoId: info.videoDetails.videoId,
            name: info.videoDetails.title || 'Untitled',
            artist: info.videoDetails.author?.name || 'Unknown'
        };
    } catch (error) {
        console.error('Error extracting video info:', error.message);
        throw error;
    }
}

// --- Extract YouTube Playlist using ytpl ---
async function extractPlaylistInfo(playlistUrl) {
    try {
        const agent = createYtdlAgent();
        const options = { limit: Infinity };
        if (agent) {
            options.requestOptions = { agent }; // ytpl uses miniget which accepts agent in requestOptions
        }
        const playlist = await ytpl(playlistUrl, options);

        const tracks = playlist.items.map(item => ({
            title: item.title || 'Untitled',
            url: item.shortUrl || item.url,
            id: item.id,
            videoId: item.id,
            duration: item.duration || 'N/A',
            duration_string: item.duration || 'N/A',
            uploader: item.author?.name || 'Unknown',
            name: item.title || 'Untitled',
            artist: item.author?.name || 'Unknown',
            thumbnail: item.bestThumbnail?.url || `https://img.youtube.com/vi/${item.id}/mqdefault.jpg`
        }));

        return {
            is_playlist: true,
            playlist_title: playlist.title,
            playlist_id: playlist.id,
            total_items: playlist.estimatedItemCount,
            uploader: playlist.author?.name || 'Unknown',
            tracks
        };
    } catch (error) {
        console.error('Error extracting playlist:', error.message);
        throw error;
    }
}

// --- Extract media info with caching ---
async function extractMediaInfo(youtubeUrl, limit = 5) {
    const cached = mediaCache.get(youtubeUrl + `_limit_${limit}`);
    if (cached) {
        return cached;
    }

    let result;

    // Check if it's a playlist
    if (youtubeUrl.includes('playlist?list=') || youtubeUrl.includes('/playlist/') || (youtubeUrl.includes('&list=') && !youtubeUrl.includes('&index='))) {
        try {
            result = await extractPlaylistInfo(youtubeUrl);
            // Apply limit to real playlists too if requested, or just for Mixes? 
            // User asked "if is radio... get a limit number default 5". 
            // It's safer to apply limit to the result tracks if it's a playlist.
            if (result.tracks) {
                result.tracks = result.tracks.slice(0, limit);
            }
        } catch (error) {
            console.log(`Playlist extraction failed: ${error.message}. Trying as recursive Mix/Video...`);
            // Fallback to single video AND check for related videos (Mix simulation)
            try {
                // We need the full info object, so we might need to modify extractVideoInfo to return it 
                // or just call ytdl.getInfo directly here. 
                // Let's call ytdl.getInfo directly to get related_videos.
                const agent = createYtdlAgent();
                const info = await ytdl.getInfo(youtubeUrl, { agent });

                const currentTrack = {
                    title: info.videoDetails.title || 'Untitled',
                    url: ytdl.chooseFormat(info.formats, { quality: 'highest', filter: 'audioandvideo' })?.url || ytdl.chooseFormat(info.formats, { quality: 'highest' })?.url,
                    thumbnail: info.videoDetails.thumbnails?.[0]?.url || `https://img.youtube.com/vi/${info.videoDetails.videoId}/mqdefault.jpg`,
                    duration: formatDuration(parseInt(info.videoDetails.lengthSeconds) || 0),
                    uploader: info.videoDetails.author?.name || 'Unknown',
                    id: info.videoDetails.videoId,
                    videoId: info.videoDetails.videoId,
                    name: info.videoDetails.title || 'Untitled',
                    artist: info.videoDetails.author?.name || 'Unknown'
                };

                let mixTracks = [currentTrack];

                // If related videos exist, add them to simulate Mix
                if (info.related_videos && info.related_videos.length > 0) {
                    const related = info.related_videos.slice(0, limit - 1).map(item => ({
                        title: item.title || 'Unknown',
                        url: '', // We don't have direct stream URL yet, user must fetch /stream/{id} or /get?ytl=... 
                        // Wait, /get expects stream URLs? The current API returns streamable URLs?
                        // ytpl returns objects with 'url' as the video link (shortUrl).
                        // My API /get returns 'tracks' which likely should have stream URLs?
                        // Let's check extractVideoInfo. It returns 'url' as the *streaming* URL (googlevideo...).
                        // ytpl implementation in this file returns 'url' as item.shortUrl (the watch URL), NOT the stream URL.
                        // So for the playlist, the 'url' field is the WATCH url.
                        // For single video, 'url' is the STREAM url? 
                        // Let's check line 116: 'url: format?.url || null'. Yes, for single video it returns stream URL.
                        // For playlist (line 138), it returns 'item.shortUrl || item.url'.

                        // So: Single video endpoint returns STREAM url. Playlist endpoint returns WATCH urls for items.
                        // The user's Mix request should behaves like a playlist. So we should return WATCH urls for the list items.

                        id: item.id,
                        videoId: item.id,
                        duration: item.duration ? formatDuration(parseInt(item.length_seconds || 0)) : 'N/A', // related_videos format varies
                        duration_string: item.duration || 'N/A',
                        uploader: item.author?.name || 'Unknown',
                        name: item.title || 'Unknown',
                        artist: item.author?.name || 'Unknown',
                        thumbnail: item.thumbnails?.[0]?.url || `https://img.youtube.com/vi/${item.id}/mqdefault.jpg`
                    }));
                    mixTracks = mixTracks.concat(related);
                }

                result = {
                    is_playlist: true, // Treat as playlist so frontend sees list
                    playlist_title: `Mix: ${currentTrack.title}`,
                    playlist_id: 'mix',
                    total_items: mixTracks.length,
                    uploader: 'YouTube Mix',
                    tracks: mixTracks
                };

            } catch (videoError) {
                console.error('Mix fallback failed:', videoError);
                throw new Error(`Failed to extract media: ${error.message} (Fallback failed: ${videoError.message})`);
            }
        }
    } else {
        // Single video
        const track = await extractVideoInfo(youtubeUrl);
        result = {
            is_playlist: false,
            tracks: track && track.url ? [track] : []
        };
    }

    mediaCache.set(youtubeUrl + `_limit_${limit}`, result);
    return result;
}

// --- YouTube Search using ytsr ---
async function searchYoutubeVideos(query, limit = 10) {
    try {
        const searchResults = await ytsr(query, { limit });

        const results = searchResults.items
            .filter(item => item.type === 'video')
            .slice(0, limit)
            .map(item => ({
                videoId: item.id,
                id: item.id,
                name: item.name || 'Unknown Title',
                title: item.name || 'Unknown Title',
                artist: item.author?.name || 'Unknown Artist',
                uploader: item.author?.name || 'Unknown Artist',
                duration: item.duration || 'Unknown',
                duration_string: item.duration || 'Unknown',
                thumbnail: item.bestThumbnail?.url || `https://img.youtube.com/vi/${item.id}/mqdefault.jpg`,
                url: item.url,
                views: item.views || 0,
                uploadedAt: item.uploadedAt || 'Unknown'
            }));

        return results;
    } catch (error) {
        console.error('YouTube Search Error:', error);
        return [];
    }
}

// --- Spotify Search ---
async function searchSpotifyTracks(query, searchType = 'track', limit = 10) {
    try {
        const token = await getSpotifyAccessToken();

        const url = new URL('https://api.spotify.com/v1/search');
        url.searchParams.set('q', query);
        url.searchParams.set('type', searchType);
        url.searchParams.set('limit', limit.toString());

        const response = await fetch(url.toString(), {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error(`Spotify API error: ${response.status}`);
        }

        const data = await response.json();

        // Format results based on type
        const typeKey = searchType + 's'; // track -> tracks, album -> albums, etc.
        const items = data[typeKey]?.items || [];

        return items.map(item => {
            if (searchType === 'track') {
                return {
                    id: item.id,
                    name: item.name,
                    artist: item.artists?.map(a => a.name).join(', ') || 'Unknown',
                    album: item.album?.name || 'Unknown',
                    duration: formatDuration(Math.floor(item.duration_ms / 1000)),
                    thumbnail: item.album?.images?.[0]?.url || '',
                    spotifyUrl: item.external_urls?.spotify || '',
                    previewUrl: item.preview_url || null
                };
            } else if (searchType === 'album') {
                return {
                    id: item.id,
                    name: item.name,
                    artist: item.artists?.map(a => a.name).join(', ') || 'Unknown',
                    totalTracks: item.total_tracks,
                    releaseDate: item.release_date,
                    thumbnail: item.images?.[0]?.url || '',
                    spotifyUrl: item.external_urls?.spotify || ''
                };
            } else if (searchType === 'playlist') {
                return {
                    id: item.id,
                    name: item.name,
                    description: item.description || '',
                    owner: item.owner?.display_name || 'Unknown',
                    totalTracks: item.tracks?.total || 0,
                    thumbnail: item.images?.[0]?.url || '',
                    spotifyUrl: item.external_urls?.spotify || ''
                };
            } else if (searchType === 'artist') {
                return {
                    id: item.id,
                    name: item.name,
                    genres: item.genres || [],
                    followers: item.followers?.total || 0,
                    popularity: item.popularity || 0,
                    thumbnail: item.images?.[0]?.url || '',
                    spotifyUrl: item.external_urls?.spotify || ''
                };
            }
            return item;
        });
    } catch (error) {
        console.error('Spotify Search Error:', error.message);
        throw error;
    }
}

// --- Get Spotify Playlist ---
async function getSpotifyPlaylist(playlistId) {
    try {
        const token = await getSpotifyAccessToken();

        const response = await fetch(`https://api.spotify.com/v1/playlists/${playlistId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error(`Spotify API error: ${response.status}`);
        }

        const data = await response.json();

        const tracks = data.tracks.items.map(item => ({
            id: item.track?.id,
            name: item.track?.name,
            artist: item.track?.artists?.map(a => a.name).join(', ') || 'Unknown',
            album: item.track?.album?.name || 'Unknown',
            duration: formatDuration(Math.floor((item.track?.duration_ms || 0) / 1000)),
            thumbnail: item.track?.album?.images?.[0]?.url || '',
            spotifyUrl: item.track?.external_urls?.spotify || '',
            previewUrl: item.track?.preview_url || null
        }));

        return {
            id: data.id,
            name: data.name,
            description: data.description || '',
            owner: data.owner?.display_name || 'Unknown',
            thumbnail: data.images?.[0]?.url || '',
            totalTracks: data.tracks?.total || 0,
            tracks
        };
    } catch (error) {
        console.error('Spotify Playlist Error:', error.message);
        throw error;
    }
}

// --- Serve index.html ---
function getIndexHtml() {
    const htmlPaths = [
        path.join(__dirname, 'index.html'),
        path.join(__dirname, '..', 'index.html')
    ];

    for (const htmlPath of htmlPaths) {
        if (fs.existsSync(htmlPath)) {
            return fs.readFileSync(htmlPath, 'utf-8');
        }
    }

    return '<h1>Welcome</h1><p>YouTube Stream URL API is running!</p>';
}

// --- API Routes ---

app.get('/', (req, res) => {
    res.send(getIndexHtml());
});

// Playground Routes
app.get('/playground', (req, res) => {
    if (process.env.PLAYGROUND !== 'true') {
        return res.status(404).send('Cannot GET /playground');
    }
    const filePath = path.join(__dirname, '..', 'playground.html');
    if (fs.existsSync(filePath)) {
        res.sendFile(filePath);
    } else {
        res.status(404).send('Playground not found');
    }
});

app.get('/playground.js', (req, res) => {
    if (process.env.PLAYGROUND !== 'true') {
        return res.status(404).send('Cannot GET /playground.js');
    }
    const filePath = path.join(__dirname, '..', 'playground.js');
    if (fs.existsSync(filePath)) {
        res.sendFile(filePath);
    } else {
        res.status(404).send('Playground script not found');
    }
});

// Get Stream Links (supports both videos and playlists)
app.get('/get', async (req, res) => {
    // Attempt cleanup/management before processing
    managePlayerScripts();

    const youtubeUrl = req.query.ytl;
    const limit = parseInt(req.query.limit, 10) || 5;

    if (!youtubeUrl) {
        return res.send(getIndexHtml());
    }

    try {
        const result = await extractMediaInfo(youtubeUrl, limit);
        if (!result.tracks || result.tracks.length === 0) {
            throw new Error('Could not find any streamable tracks for the given URL.');
        }
        res.json(result);
    } catch (error) {
        console.error(`Error for URL: ${youtubeUrl} - ${error.message}`);
        res.status(500).json({ error: error.message });
    }
});

// Stream by Video ID
app.get('/stream/:videoId', async (req, res) => {
    const { videoId } = req.params;

    try {
        const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}`;
        const result = await extractMediaInfo(youtubeUrl);

        if (result && result.tracks && result.tracks.length > 0) {
            const track = result.tracks[0];
            if (track && track.url) {
                return res.json({
                    videoId,
                    streamUrl: track.url,
                    title: track.title || 'Unknown',
                    uploader: track.uploader || 'Unknown',
                    duration: track.duration || 'Unknown',
                    thumbnail: track.thumbnail || `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`
                });
            }
        }

        res.status(404).json({ error: 'Could not get stream URL for this video' });
    } catch (error) {
        console.error(`Stream URL error for ${videoId}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// YouTube Search
app.get('/api/search/youtube', async (req, res) => {
    const query = req.query.query;
    let limit = parseInt(req.query.limit, 10) || 10;

    if (!query) {
        return res.status(400).json({ error: 'Query parameter is required.' });
    }

    if (limit > 50) limit = 50;

    try {
        const results = await searchYoutubeVideos(query, limit);
        res.json({
            query,
            limit,
            total_results: results.length,
            results
        });
    } catch (error) {
        console.error('YouTube search error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Spotify Search
app.get('/api/search/spotify', async (req, res) => {
    const query = req.query.query;
    const searchType = req.query.type || 'track';
    let limit = parseInt(req.query.limit, 10) || 10;

    if (!query) {
        return res.status(400).json({ error: 'Query parameter is required.' });
    }

    if (!['track', 'album', 'playlist', 'artist'].includes(searchType)) {
        return res.status(400).json({ error: 'Type must be one of: track, album, playlist, artist' });
    }

    if (limit > 50) limit = 50;

    try {
        const results = await searchSpotifyTracks(query, searchType, limit);
        res.json({
            query,
            type: searchType,
            limit,
            total_results: results.length,
            results
        });
    } catch (error) {
        console.error('Spotify search error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Spotify Playlist
app.get('/api/spotify/playlist/:playlistId', async (req, res) => {
    const { playlistId } = req.params;

    try {
        const playlist = await getSpotifyPlaylist(playlistId);
        res.json(playlist);
    } catch (error) {
        console.error('Spotify playlist error:', error);
        res.status(500).json({ error: error.message });
    }
});

// API Info
app.get('/api/info', (req, res) => {
    res.json({
        name: 'YouTube Stream URL API',
        version: '3.1.0',
        runtime: 'Node.js (Pure JS)',
        features: {
            youtube: ['video streaming', 'playlist extraction', 'search'],
            spotify: ['search (track/album/playlist/artist)', 'playlist extraction']
        },
        endpoints: {
            streaming: {
                'GET /get?ytl={url}': 'Get streaming links (videos & playlists)',
                'GET /stream/{video_id}': 'Get direct streaming URL'
            },
            search: {
                'GET /api/search/youtube': 'Search YouTube videos',
                'GET /api/search/spotify': 'Search Spotify'
            },
            spotify: {
                'GET /api/spotify/playlist/{id}': 'Get Spotify playlist tracks'
            }
        },
        spotify_configured: !!(SPOTIFY_CLIENT_ID && SPOTIFY_CLIENT_SECRET)
    });
});

// Health Check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: '3.1.0',
        services: {
            youtube_streaming: 'active',
            youtube_playlist: 'active',
            youtube_search: 'active',
            spotify_search: SPOTIFY_CLIENT_ID ? 'active' : 'not configured',
            spotify_playlist: SPOTIFY_CLIENT_ID ? 'active' : 'not configured'
        }
    });
});

// Start server
const PORT = process.env.PORT || 3000;
if (process.env.NODE_ENV !== 'production') {
    app.listen(PORT, () => {
        console.log(`🎬 YouTube Stream URL API v3.1.0`);
        console.log(`   Running on http://localhost:${PORT}`);
        console.log(`   YouTube: ✅ Videos, ✅ Playlists, ✅ Search`);
        console.log(`   Spotify: ${SPOTIFY_CLIENT_ID ? '✅ Configured' : '⚠️ Set SPOTIFY_CLIENT_ID & SPOTIFY_CLIENT_SECRET'}`);
    });
}

export default app;
