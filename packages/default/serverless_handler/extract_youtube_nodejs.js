#!/usr/bin/env node

/**
 * Node.js YouTube Stream Extractor
 *
 * Called from Python serverless handler as subprocess when JS runtime is needed
 * for YouTube signature solving.
 *
 * Usage: node extract_youtube_nodejs.js <videoId> [cookiesFile]
 * Output: JSON to stdout
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import ytdl from '@distube/ytdl-core';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function parseNetscapeCookies(content) {
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

async function extractYoutubeStream(videoId, cookiesPath = null) {
    try {
        const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}`;
        console.error(`[NODE] Extracting: ${youtubeUrl}`);

        let agent = undefined;

        // Load cookies if available
        if (cookiesPath && fs.existsSync(cookiesPath)) {
            try {
                const cookieContent = fs.readFileSync(cookiesPath, 'utf-8');
                let cookies = null;

                // Try JSON first
                try {
                    cookies = JSON.parse(cookieContent);
                } catch (e) {
                    // Try Netscape format
                    cookies = await parseNetscapeCookies(cookieContent);
                }

                if (cookies && Array.isArray(cookies) && cookies.length > 0) {
                    console.error(`[NODE] Found ${cookies.length} cookies, creating agent...`);
                    agent = ytdl.createAgent(cookies);
                } else {
                    console.error(`[NODE] Cookie file empty or invalid`);
                }
            } catch (err) {
                console.error(`[NODE] Error loading cookies: ${err.message}`);
            }
        } else if (cookiesPath) {
            console.error(`[NODE] Cookies file not found: ${cookiesPath}`);
        }

        // Extract video info
        console.error(`[NODE] Calling ytdl.getInfo...`);
        const info = await ytdl.getInfo(youtubeUrl, { agent });

        // Choose best format
        const format = ytdl.chooseFormat(info.formats, {
            quality: 'highest',
            filter: 'audioandvideo'
        }) || ytdl.chooseFormat(info.formats, { quality: 'highest' });

        if (!format || !format.url) {
            throw new Error('No suitable format found');
        }

        const result = {
            title: info.videoDetails.title || 'Unknown',
            url: format.url,
            thumbnail: info.videoDetails.thumbnails?.[0]?.url || `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`,
            duration: String(info.videoDetails.lengthSeconds || 0),
            uploader: info.videoDetails.author?.name || 'Unknown',
            id: videoId,
            videoId: videoId,
            format_id: format.itag,
            ext: format.container || 'mp4',
            resolution: format.qualityLabel || 'unknown'
        };

        console.error(`[NODE] Success: ${result.title}`);
        console.log(JSON.stringify(result));
        process.exit(0);

    } catch (error) {
        const errorResponse = {
            error: 'Failed to extract stream',
            reason: error.message,
            videoId: videoId
        };

        console.error(`[NODE] Error: ${error.message}`);
        console.log(JSON.stringify(errorResponse));
        process.exit(1);
    }
}

// Main
async function main() {
    const args = process.argv.slice(2);

    if (args.length === 0) {
        const err = { error: 'Missing videoId argument' };
        console.log(JSON.stringify(err));
        process.exit(1);
    }

    const videoId = args[0];
    const cookiesPath = args[1] || null;

    await extractYoutubeStream(videoId, cookiesPath);
}

main().catch(err => {
    console.log(JSON.stringify({ error: err.message, videoId: process.argv[2] }));
    process.exit(1);
});
