/**
 * Digital Ocean Serverless Function for YouTube Video Extraction
 * Supports downloading audio and video formats
 */

import ytdl from '@distube/ytdl-core';

/**
 * Main handler function for Digital Ocean
 * @param {Object} event - The event object from Digital Ocean
 * @param {Object} context - The context object from Digital Ocean
 * @returns {Object} Response object with statusCode, headers, and body
 */
export async function main(event, context) {
    // Enable CORS
    const headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    };

    // Handle OPTIONS request for CORS preflight
    if (event.httpMethod === 'OPTIONS') {
        return {
            statusCode: 200,
            headers,
            body: ''
        };
    }

    try {
        // Parse query parameters or body
        const params = event.queryStringParameters || {};
        const body = event.body ? JSON.parse(event.body) : {};
        const videoUrl = params.url || body.url;
        const format = params.format || body.format || 'video'; // 'video' or 'audio'
        const quality = params.quality || body.quality || 'highest';

        // Validate input
        if (!videoUrl) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({
                    error: 'Missing required parameter: url',
                    message: 'Please provide a YouTube video URL'
                })
            };
        }

        // Validate YouTube URL
        if (!ytdl.validateURL(videoUrl)) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({
                    error: 'Invalid YouTube URL',
                    message: 'Please provide a valid YouTube video URL'
                })
            };
        }

        // Extract video ID
        const videoId = ytdl.getURLVideoID(videoUrl);

        // Get video info
        const info = await ytdl.getInfo(videoUrl);

        // Filter formats based on request
        let formats;
        if (format === 'audio') {
            formats = ytdl.filterFormats(info.formats, 'audioonly');
        } else {
            formats = ytdl.filterFormats(info.formats, 'videoandaudio');
        }

        // Sort by quality
        if (quality === 'highest') {
            formats.sort((a, b) => b.bitrate - a.bitrate);
        } else if (quality === 'lowest') {
            formats.sort((a, b) => a.bitrate - b.bitrate);
        }

        // Select the best format
        const selectedFormat = formats[0];

        if (!selectedFormat) {
            return {
                statusCode: 404,
                headers,
                body: JSON.stringify({
                    error: 'No suitable format found',
                    message: `No ${format} format available for this video`
                })
            };
        }

        // Prepare response
        const response = {
            success: true,
            videoId: videoId,
            title: info.videoDetails.title,
            author: info.videoDetails.author.name,
            lengthSeconds: info.videoDetails.lengthSeconds,
            thumbnail: info.videoDetails.thumbnails[info.videoDetails.thumbnails.length - 1].url,
            description: info.videoDetails.description,
            format: {
                type: format,
                quality: selectedFormat.qualityLabel || selectedFormat.audioBitrate + 'kbps',
                container: selectedFormat.container,
                codec: selectedFormat.codecs,
                bitrate: selectedFormat.bitrate,
                url: selectedFormat.url
            },
            downloadUrl: selectedFormat.url,
            availableFormats: {
                video: ytdl.filterFormats(info.formats, 'videoandaudio').length,
                audio: ytdl.filterFormats(info.formats, 'audioonly').length
            }
        };

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(response)
        };

    } catch (error) {
        console.error('Error processing request:', error);
        
        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({
                error: 'Internal Server Error',
                message: error.message || 'Failed to extract video information'
            })
        };
    }
}

// For local testing
if (process.env.NODE_ENV === 'development') {
    const testEvent = {
        httpMethod: 'GET',
        queryStringParameters: {
            url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            format: 'video'
        }
    };
    
    main(testEvent, {}).then(result => {
        console.log('Test result:', JSON.stringify(result, null, 2));
    }).catch(err => {
        console.error('Test error:', err);
    });
}
