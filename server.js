const express = require('express');
const path = require('path');
const fetch = require('node-fetch');
const cheerio = require('cheerio');
const { scrapeFacebookVideo } = require('./scraper.js');
const { scrapeFacebookPhoto } = require('./photo_scraper.js');
const { exec } = require('child_process');
const fs = require('fs');

// Optional Facebook Graph API token (set as environment variable)
const FACEBOOK_TOKEN = process.env.FACEBOOK_TOKEN || '';

async function getImagesFromGraph(fbid) {
    if (!FACEBOOK_TOKEN) return [];
    try {
        const graphUrl = `https://graph.facebook.com/v18.0/${fbid}?fields=images&access_token=${FACEBOOK_TOKEN}`;
        console.log(`Fetching Graph API for images: ${graphUrl}`);
        const resp = await fetch(graphUrl);
        if (!resp.ok) {
            console.log(`Graph API failed: ${resp.status} ${await resp.text()}`);
            return [];
        }
        const data = await resp.json();
        if (data && data.images && Array.isArray(data.images)) {
            // Sort by width descending
            const sorted = data.images.sort((a, b) => (b.width || 0) - (a.width || 0));
            return sorted.map(img => img.source);
        }
    } catch (err) {
        console.log('Graph API error:', err.message);
    }
    return [];
}

const app = express();
const port = process.env.PORT || 10000;

// Middleware to parse JSON bodies
app.use(express.json());

// Serve static files from the "public" directory
app.use(express.static(path.join(__dirname, 'public')));

// Health check endpoint for Render
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Serve Facebook.html as the main page
app.get('/', (req, res) => {
    const htmlPath = path.join(__dirname, 'public', 'Facebook.html');
    // Check if the file exists
    if (fs.existsSync(htmlPath)) {
        res.sendFile(htmlPath);
    } else {
        // Fallback response if HTML file is missing
        res.status(200).send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>FreeFBZone</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; text-align: center; }
                    h1 { color: #1877f2; }
                </style>
            </head>
            <body>
                <h1>FreeFBZone Server</h1>
                <p>Server is running successfully on port ${port}</p>
                <p>API Endpoints Available:</p>
                <ul style="list-style: none; padding: 0;">
                    <li>/scrape - Scrape Facebook video</li>
                    <li>/description - Get video description</li>
                    <li>/health - Health check</li>
                </ul>
            </body>
            </html>
        `);
    }
});

// API endpoint for description
app.get('/description', async (req, res) => {
    const { url } = req.query;
    if (!url) return res.status(400).json({ error: 'Missing url param' });

    try {
        // First try using simple fetch with Cheerio
        try {
            const headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' };
            const html = await (await fetch(url, { headers })).text();
            const $ = cheerio.load(html);

            const rawTitle = $('meta[property="og:title"]').attr('content') || '';
            const match = rawTitle.match(/\|\s*([^|]+?)\s*\|/);
            const title = match ? match[1].trim() : rawTitle.split('|')[0].trim();

            // Try to get description from meta tags
            const description = $('meta[property="og:description"]').attr('content') || '';
            
            if (title || description) {
                return res.json({ title, description });
            }
        } catch (cheerioError) {
            console.log('Error using Cheerio approach:', cheerioError.message);
        }

        // If Cheerio approach fails or doesn't find data, use the full scraper
        console.log('Falling back to puppeteer scraping for description');
        const data = await scrapeFacebookVideo(url);
        res.json({ 
            title: data.creator || '',
            description: data.description || ''
        });
    } catch (e) {
        console.error('Description scraping failed:', e);
        res.status(500).json({ error: 'Scrape failed' });
    }
});

// API endpoint for scraping
app.get('/scrape', async (req, res) => {
    const { url } = req.query;

    if (!url) {
        return res.status(400).json({ error: 'URL is required' });
    }

    try {
        const data = await scrapeFacebookVideo(url);
        res.json(data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// API endpoint for using external download service (snapsave.app)
app.post('/use-snapsave', (req, res) => {
    const { url } = req.body;
    
    if (!url) {
        return res.status(400).json({ error: 'URL is required' });
    }
    
    try {
        console.log(`Processing SnapSave download request for URL: ${url}`);
        
        // Run the Python script to handle the download
        // Use python3 on Linux/Render, python on Windows
        const pythonCmd = process.platform === 'win32' ? 'python' : '/opt/venv/bin/python';
        const command = `${pythonCmd} snapsave_downloader.py "${url}"`;
        
        exec(command, (error, stdout, stderr) => {
            if (error) {
                console.error(`Error executing Python script: ${error.message}`);
                return res.status(500).json({ error: 'Download failed: An internal server error occurred.' });
            }
            
            if (stderr) {
                console.error(`Python script stderr: ${stderr}`);
                // For now, don't send stderr directly to the client unless it's a specific error message
                // return res.status(500).json({ error: `Python script error: ${stderr}` });
            }
            
            console.log(`Python script output: ${stdout}`);
            
            // Parse the stdout to extract the download link
            const match = stdout.match(/DOWNLOAD_LINK:(.*)/);
            if (match && match[1]) {
                const downloadLink = match[1].trim();
                return res.json({
                    success: true,
                    message: 'Download link retrieved successfully',
                    downloadLink: downloadLink // Send the download link to the client
                });
            }
            
            // If we can't extract the link from stdout
            return res.json({
                success: false,
                error: stdout.includes('Error:') ? stdout.split('Error:')[1].trim() : 'Could not extract download link from script output.'
            });
        });
    } catch (error) {
        console.error('Error in /use-snapsave endpoint:', error);
        res.status(500).json({ error: 'Download failed: An unexpected server error occurred.' });
    }
});

// New proxy endpoint for controlled downloads with custom filename
app.get('/download-proxy', async (req, res) => {
    const { url } = req.query;
    const filename = 'freefbzone_hdvideo.mp4'; // Your desired custom filename

    if (!url) {
        return res.status(400).send('Missing download URL');
    }

    try {
        console.log(`Proxying download for: ${url} with filename: ${filename}`);
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`Failed to fetch file from external URL: ${response.statusText}`);
        }

        // Set Content-Disposition header to control filename
        res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
        
        // Stream the data directly to the client
        response.body.pipe(res);

    } catch (error) {
        console.error('Error in download-proxy:', error);
        res.status(500).send(`Failed to download file: ${error.message}`);
    }
});

// Creator logo/profile picture download endpoints have been removed
// New implementation will be added

// New endpoint for scraping high-quality Facebook photos
app.get('/scrape-photo', async (req, res) => {
    const { url } = req.query;
    
    if (!url) {
        return res.status(400).json({ error: 'URL parameter is required' });
    }
    
    try {
        console.log(`Scraping Facebook photo for high-quality URL: ${url}`);
        
        // Use puppeteer to scrape the actual high-quality image URLs
        const scrapeResult = await scrapeFacebookPhoto(url);
        
        if (!scrapeResult.success || scrapeResult.imageUrls.length === 0) {
            return res.status(404).json({ 
                error: 'Could not find any images on the page',
                details: scrapeResult.error 
            });
        }
        
        console.log(`Found ${scrapeResult.imageUrls.length} image URLs`);
        
        // Try to download the largest/highest quality image
        let bestImage = null;
        let bestImageSize = 0;
        
        for (const imageUrl of scrapeResult.imageUrls) {
            try {
                console.log(`Testing image URL: ${imageUrl}`);
                
                const response = await fetch(imageUrl, {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'Sec-Fetch-Dest': 'image',
                        'Sec-Fetch-Mode': 'no-cors',
                        'Sec-Fetch-Site': 'cross-site'
                    },
                    redirect: 'follow'
                });
                
                if (response.ok) {
                    const contentType = response.headers.get('content-type');
                    const contentLength = parseInt(response.headers.get('content-length') || '0');
                    
                    console.log(`Image content-type: ${contentType}, size: ${contentLength}`);
                    
                    if (contentType && contentType.startsWith('image/') && contentLength > bestImageSize) {
                        const imageBuffer = await response.buffer();
                        
                        // Validate it's actually an image
                        const isPNG = imageBuffer[0] === 0x89 && imageBuffer[1] === 0x50;
                        const isJPEG = imageBuffer[0] === 0xFF && imageBuffer[1] === 0xD8;
                        const isWebP = imageBuffer.length > 12 && imageBuffer[8] === 0x57 && imageBuffer[9] === 0x45;
                        
                        if (isPNG || isJPEG || isWebP) {
                            bestImage = {
                                buffer: imageBuffer,
                                contentType: contentType,
                                size: imageBuffer.length,
                                url: imageUrl
                            };
                            bestImageSize = imageBuffer.length;
                            console.log(`Found better image: ${imageBuffer.length} bytes`);
                        }
                    }
                }
            } catch (error) {
                console.log(`Failed to fetch ${imageUrl}: ${error.message}`);
                continue;
            }
        }
        
        if (!bestImage) {
            return res.status(404).json({ 
                error: 'Could not download any valid images',
                triedUrls: scrapeResult.imageUrls 
            });
        }
        
        // Determine file extension
        let fileExtension = 'jpg';
        if (bestImage.contentType.includes('png')) {
            fileExtension = 'png';
        } else if (bestImage.contentType.includes('webp')) {
            fileExtension = 'webp';
        }
        
        // Send the best quality image
        res.setHeader('Content-Type', bestImage.contentType);
        res.setHeader('Content-Disposition', `attachment; filename="Freefbzone_HD_photo.${fileExtension}"`);
        res.setHeader('Content-Length', bestImage.size);
        res.setHeader('X-Image-Source-URL', bestImage.url);
        
        res.send(bestImage.buffer);
        
        console.log(`Successfully sent ${fileExtension.toUpperCase()} image (${bestImage.size} bytes) from ${bestImage.url}`);
        
    } catch (error) {
        console.error('Error in photo scraping:', error);
        res.status(500).json({ error: 'Failed to scrape photo: ' + error.message });
    }
});


// Audio download endpoint - integrated approach
app.post('/download-audio', async (req, res) => {
    const { videoUrl } = req.body;
    
    if (!videoUrl) {
        return res.status(400).json({ error: 'Video URL is required' });
    }
    
    try {
        console.log(`Processing audio download request: ${videoUrl}`);
        
        // Use the Python script directly to process audio
        // Use python3 on Linux/Render, python on Windows
        const pythonCmd = process.platform === 'win32' ? 'python' : '/opt/venv/bin/python';
        const command = `${pythonCmd} audio.py "${videoUrl}"`;
        
        exec(command, { timeout: 300000 }, (error, stdout, stderr) => {
            if (error) {
                console.error(`Error executing Python audio script: ${error.message}`);
                return res.status(500).json({ error: 'Audio processing failed: An internal server error occurred.' });
            }
            
            if (stderr) {
                console.error(`Python audio script stderr: ${stderr}`);
            }
            
            console.log(`Python audio script output: ${stdout}`);
            
            // Check if the script indicates success and extract the audio file path
            const match = stdout.match(/Audio file ready: (.*)/);
            if (match && match[1]) {
                const audioFilePath = match[1].trim();
                
                if (fs.existsSync(audioFilePath)) {
                    console.log(`Audio file found: ${audioFilePath}`);
                    
                    // Set headers for MP3 download
                    res.setHeader('Content-Type', 'audio/mpeg');
                    res.setHeader('Content-Disposition', 'attachment; filename="freefbzone_audio.mp3"');
                    
                    // Create read stream and pipe to response
                    const fileStream = fs.createReadStream(audioFilePath);
                    fileStream.pipe(res);
                    
                    // Clean up file after sending
                    fileStream.on('end', () => {
                        try {
                            fs.unlinkSync(audioFilePath);
                            console.log(`Cleaned up audio file: ${audioFilePath}`);
                        } catch (cleanupError) {
                            console.error(`Failed to cleanup audio file: ${cleanupError.message}`);
                        }
                    });
                    
                    fileStream.on('error', (streamError) => {
                        console.error(`Error streaming audio file: ${streamError.message}`);
                        if (!res.headersSent) {
                            res.status(500).json({ error: 'Failed to stream audio file' });
                        }
                    });
                } else {
                    return res.status(500).json({ error: 'Audio file was not created' });
                }
            } else {
                // Extract error message from stdout if available
                const errorMatch = stdout.match(/\[ERROR\](.*)/);
                const errorMessage = errorMatch ? errorMatch[1].trim() : 'Audio processing failed';
                return res.status(500).json({ error: errorMessage });
            }
        });
        
    } catch (error) {
        console.error('Error in audio download endpoint:', error);
        res.status(500).json({ error: 'Audio download failed: ' + error.message });
    }
});

app.listen(port, () => {
    console.log(`Server is running! Open http://localhost:${port} in your browser.`);
});
