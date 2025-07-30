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
const port = process.env.PORT || 3000;

// Middleware to parse JSON bodies
app.use(express.json());

// Serve static files from the "public" directory
app.use(express.static(path.join(__dirname, 'public')));

// Serve Facebook.html as the main page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'Facebook.html'));
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
        const command = `python snapsave_downloader.py "${url}"`;
        
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

// New endpoint for downloading profile pictures with proper validation
app.get('/download-profile-picture', async (req, res) => {
    const { url } = req.query;
    
    if (!url) {
        return res.status(400).json({ error: 'URL parameter is required' });
    }
    
    try {
        console.log(`Processing profile picture download for: ${url}`);
        
        // Try multiple URL transformation methods
        const urlsToTry = [
            // Method 1: Handle Facebook photo URLs with fbid parameter
            (() => {
                if (url.includes('facebook.com/photo') && url.includes('fbid=')) {
                    const fbidMatch = url.match(/fbid=([0-9]+)/);
                    if (fbidMatch && fbidMatch[1]) {
                        // Try different Facebook CDN endpoints for the photo
                        const fbid = fbidMatch[1];
                        // Facebook image size suffixes:
                        // _o = original (highest quality)
                        // _b = large (~960px)
                        // _n = normal (~720px)
                        // _t = thumbnail
                        return [
                            // Try original quality first
                            `https://scontent.xx.fbcdn.net/v/t39.30808-6/${fbid}_o.jpg`,
                            `https://scontent.xx.fbcdn.net/v/t1.6435-9/${fbid}_o.jpg`,
                            `https://scontent.xx.fbcdn.net/v/t39.30808-6/p2048x2048/${fbid}_o.jpg`,
                            // Then try large size
                            `https://scontent.xx.fbcdn.net/v/t39.30808-6/${fbid}_b.jpg`,
                            `https://scontent.xx.fbcdn.net/v/t1.6435-9/${fbid}_b.jpg`,
                            // Normal size as fallback
                            `https://scontent.xx.fbcdn.net/v/t39.30808-6/${fbid}_n.jpg`,
                            `https://scontent.xx.fbcdn.net/v/t1.6435-9/${fbid}_n.jpg`,
                            // Try with resolution parameters
                            `https://scontent.xx.fbcdn.net/v/t39.30808-6/p2048x2048/${fbid}_n.jpg`,
                            `https://scontent.xx.fbcdn.net/v/t1.6435-9/p2048x2048/${fbid}_n.jpg`
                        ];
                    }
                }
                return [];
            })().flat(),
            
            // Method 2: Remove all parameters and add bypass
            url.split('?')[0] + '?_nc_bypass_redirects=true',
            
            // Method 3: Extract user ID and use Graph API (if possible)
            (() => {
                const userIdMatch = url.match(new RegExp('/([0-9]+)/')); 
                if (userIdMatch && userIdMatch[1]) {
                    return `https://graph.facebook.com/${userIdMatch[1]}/picture?type=large&redirect=0`;
                }
                return null;
            })(),
            
            // Method 4: Clean scontent URLs
            (() => {
                if (url.includes('scontent') || url.includes('fbcdn')) {
                    const baseUrl = url.split('?')[0];
                    return baseUrl;
                }
                return null;
            })(),
            
            // Method 5: Try to construct direct image URLs from Facebook photo URLs
            (() => {
                if (url.includes('facebook.com/photo')) {
                    // Try to extract any numeric IDs from the URL
                    const numericMatches = url.match(/[0-9]{10,}/g);
                    if (numericMatches && numericMatches.length > 0) {
                        return numericMatches.map(id => [
                            // Try original quality first
                            `https://scontent.xx.fbcdn.net/v/t39.30808-6/${id}_o.jpg`,
                            `https://scontent.xx.fbcdn.net/v/t1.6435-9/${id}_o.jpg`,
                            // Large size
                            `https://scontent.xx.fbcdn.net/v/t39.30808-6/${id}_b.jpg`,
                            `https://scontent.xx.fbcdn.net/v/t1.6435-9/${id}_b.jpg`,
                            // Normal size
                            `https://scontent.xx.fbcdn.net/v/t39.30808-6/${id}_n.jpg`,
                            `https://scontent.xx.fbcdn.net/v/t1.6435-9/${id}_n.jpg`
                        ]).flat();
                    }
                }
                return [];
            })().flat(),
            
            // Method 6: Original URL as fallback
            url
        ].flat().filter(Boolean); // Remove null values and flatten arrays
        
        let imageResponse = null;
        let workingUrl = null;
        
        // Function to enhance image quality by modifying URL
        const enhanceImageQuality = (originalUrl) => {
            let enhancedUrls = []; // Start empty to control priority order
            
            try {
                // Method 1: Ultra-high resolution attempts (highest priority)
                if (originalUrl.includes('scontent') || originalUrl.includes('fbcdn')) {
                    const parts = originalUrl.split('/');
                    const filename = parts[parts.length - 1];
                    const basePath = parts.slice(0, -1).join('/');
                    
                    // Try ultra-high resolutions first (8K, 4K, 2K)
                    const ultraHighResUrls = [
                        `${basePath}/p8192x8192/${filename.replace(/_[nstbm]\./g, '_o.')}`,
                        `${basePath}/p4096x4096/${filename.replace(/_[nstbm]\./g, '_o.')}`,
                        `${basePath}/p2048x2048/${filename.replace(/_[nstbm]\./g, '_o.')}`,
                        `${basePath}/p1920x1920/${filename.replace(/_[nstbm]\./g, '_o.')}`,
                        `${basePath}/p1080x1080/${filename.replace(/_[nstbm]\./g, '_o.')}`
                    ];
                    enhancedUrls.push(...ultraHighResUrls);
                }
                
                // Method 2: Replace ALL size suffixes with original quality
                if (originalUrl.includes('_n.') || originalUrl.includes('_s.') || originalUrl.includes('_t.') || 
                    originalUrl.includes('_b.') || originalUrl.includes('_m.')) {
                    // Original quality without any size constraints
                    const originalQualityUrl = originalUrl.replace(/_[nstbm]\./g, '_o.');
                    enhancedUrls.push(originalQualityUrl);
                    console.log(`Enhanced to original quality: ${originalQualityUrl}`);
                    
                    // Also try with maximum resolution parameter
                    const parts = originalQualityUrl.split('/');
                    const filename = parts[parts.length - 1];
                    const basePath = parts.slice(0, -1).join('/');
                    enhancedUrls.push(`${basePath}/p8192x8192/${filename}`);
                }
                
                // Method 3: Extract image ID and construct direct URLs
                const imageIdMatch = originalUrl.match(/\/(\d{10,})_/);
                if (imageIdMatch && imageIdMatch[1]) {
                    const imageId = imageIdMatch[1];
                    const directUrls = [
                        // Try different Facebook image API endpoints
                        `https://scontent.xx.fbcdn.net/v/t39.30808-6/p8192x8192/${imageId}_o.jpg`,
                        `https://scontent.xx.fbcdn.net/v/t1.6435-9/p8192x8192/${imageId}_o.jpg`,
                        `https://scontent.xx.fbcdn.net/v/t39.30808-6/${imageId}_o.jpg`,
                        `https://scontent.xx.fbcdn.net/v/t1.6435-9/${imageId}_o.jpg`,
                        // PNG variants for higher quality
                        `https://scontent.xx.fbcdn.net/v/t39.30808-6/p8192x8192/${imageId}_o.png`,
                        `https://scontent.xx.fbcdn.net/v/t1.6435-9/p8192x8192/${imageId}_o.png`
                    ];
                    enhancedUrls.push(...directUrls);
                    console.log(`Added direct image ID URLs for ID: ${imageId}`);
                }
                
                // Method 4: Try different CDN endpoints with geographic distribution
                if (originalUrl.includes('scontent.xx.fbcdn.net')) {
                    const cdnVariants = [
                        originalUrl.replace('scontent.xx.fbcdn.net', 'scontent-lax3-2.xx.fbcdn.net'),
                        originalUrl.replace('scontent.xx.fbcdn.net', 'scontent-sjc3-2.xx.fbcdn.net'),
                        originalUrl.replace('scontent.xx.fbcdn.net', 'scontent-atl3-2.xx.fbcdn.net'),
                        originalUrl.replace('scontent.xx.fbcdn.net', 'scontent-iad3-2.xx.fbcdn.net'),
                        originalUrl.replace('scontent.xx.fbcdn.net', 'scontent-ord5-2.xx.fbcdn.net')
                    ];
                    // Apply quality enhancements to CDN variants too
                    cdnVariants.forEach(cdn => {
                        enhancedUrls.push(cdn.replace(/_[nstbm]\./g, '_o.'));
                        // Add high-res versions of CDN variants
                        const parts = cdn.split('/');
                        const filename = parts[parts.length - 1].replace(/_[nstbm]\./g, '_o.');
                        const basePath = parts.slice(0, -1).join('/');
                        enhancedUrls.push(`${basePath}/p4096x4096/${filename}`);
                    });
                }
                
                // Method 5: Remove ALL query parameters that might limit quality
                const cleanUrl = originalUrl.split('?')[0].split('#')[0];
                enhancedUrls.push(cleanUrl);
                
                // Method 6: Try alternative image formats (PNG for lossless quality)
                if (originalUrl.includes('.jpg')) {
                    enhancedUrls.push(originalUrl.replace('.jpg', '.png'));
                    enhancedUrls.push(cleanUrl.replace('.jpg', '.png'));
                }
                
                // Method 7: Original URL as final fallback
                enhancedUrls.push(originalUrl);
                
            } catch (error) {
                console.log(`Error enhancing URL: ${error.message}`);
            }
            
            // Remove duplicates while preserving order (highest quality first)
            return [...new Set(enhancedUrls)];
        };
        
        // Try each URL until we find one that returns a valid image
        for (const testUrl of urlsToTry) {
            // Get enhanced quality versions of this URL
            const enhancedUrls = enhanceImageQuality(testUrl);
            
            for (const enhancedUrl of enhancedUrls) {
                try {
                    console.log(`Trying enhanced URL: ${enhancedUrl}`);
                    
                    const response = await fetch(enhancedUrl, {
                        headers: {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        },
                        redirect: 'follow'
                    });
                    
                    if (response.ok) {
                        const contentType = response.headers.get('content-type');
                        const contentLength = response.headers.get('content-length');
                        console.log(`Response content-type: ${contentType}, size: ${contentLength} bytes`);
                        
                        // Check if it's actually an image
                        if (contentType && contentType.startsWith('image/')) {
                            imageResponse = response;
                            workingUrl = enhancedUrl;
                            console.log(`Found valid HIGH QUALITY image at: ${workingUrl}`);
                            
                            // If this is an original quality or ultra-high-res image, use it immediately
                            if (enhancedUrl.includes('_o.') || 
                                enhancedUrl.includes('/p8192x8192/') || 
                                enhancedUrl.includes('/p4096x4096/') || 
                                enhancedUrl.includes('/p2048x2048/') ||
                                enhancedUrl.includes('.png')) {
                                console.log('Found original/ultra-high-res quality image, using this one!');
                                break;
                            }
                        } else {
                            console.log(`Not an image, content-type: ${contentType}`);
                        }
                    }
                } catch (error) {
                    console.log(`Failed to fetch ${enhancedUrl}: ${error.message}`);
                    continue;
                }
            }
            
            // If we found a good image, break from outer loop
            if (imageResponse) break;
        }
        
        if (!imageResponse) {
            return res.status(404).json({ error: 'Could not find a valid profile picture image' });
        }
        
        // Get the image buffer
        const imageBuffer = await imageResponse.buffer();
        
        // Validate that it's actually an image by checking the first few bytes
        const isPNG = imageBuffer[0] === 0x89 && imageBuffer[1] === 0x50 && imageBuffer[2] === 0x4E && imageBuffer[3] === 0x47;
        const isJPEG = imageBuffer[0] === 0xFF && imageBuffer[1] === 0xD8;
        const isWebP = imageBuffer[8] === 0x57 && imageBuffer[9] === 0x45 && imageBuffer[10] === 0x42 && imageBuffer[11] === 0x50;
        
        if (!isPNG && !isJPEG && !isWebP) {
            return res.status(400).json({ error: 'Downloaded content is not a valid image file' });
        }
        
        // Determine file extension based on content
        let fileExtension = 'jpg';
        let mimeType = 'image/jpeg';
        
        if (isPNG) {
            fileExtension = 'png';
            mimeType = 'image/png';
        } else if (isWebP) {
            fileExtension = 'webp';
            mimeType = 'image/webp';
        }
        
        // Set proper headers for image download
        res.setHeader('Content-Type', mimeType);
        res.setHeader('Content-Disposition', `attachment; filename="Freefbzone_logo.${fileExtension}"`);
        res.setHeader('Content-Length', imageBuffer.length);
        
        // Send the image
        res.send(imageBuffer);
        
        console.log(`Successfully sent ${fileExtension.toUpperCase()} image (${imageBuffer.length} bytes)`);
        
    } catch (error) {
        console.error('Error in profile picture download:', error);
        res.status(500).json({ error: 'Failed to download profile picture: ' + error.message });
    }
});

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

// New endpoint for downloading creator logo from VIDEO URL using full automation pipeline
app.post('/download-creator-logo-from-video', async (req, res) => {
    const { videoUrl } = req.body;
    
    if (!videoUrl) {
        return res.status(400).json({ error: 'Video URL is required' });
    }
    
    try {
        console.log(`Processing creator logo download from video URL: ${videoUrl}`);
        
        // Use fixed filename for the logo
        const outputFile = 'freefbzone_logo.png';
        
        // Run auto_fb.py with the VIDEO URL in non-interactive mode
        const command = `python auto_fb.py --video-url "${videoUrl}" --output-file "${outputFile}"`;
        
        exec(command, { timeout: 300000 }, (error, stdout, stderr) => {
            if (error) {
                console.error(`Error executing auto_fb.py: ${error.message}`);
                return res.status(500).json({ error: 'Automation failed: An internal server error occurred.' });
            }
            
            if (stderr) {
                console.error(`auto_fb.py stderr: ${stderr}`);
            }
            
            console.log(`auto_fb.py output: ${stdout}`);
            
            // Check if automation was successful
            if (stdout.includes('AUTOMATION_SUCCESS')) {
                // Look for any downloaded profile image files
                const possibleFiles = [
                    outputFile,
                    'facebook_profile_image.jpg',
                    'creator_logo.png',
                    // Check for any recently created image files
                    ...fs.readdirSync('.').filter(file => 
                        (file.includes('logo') || file.includes('profile') || file.includes('facebook')) &&
                        (file.endsWith('.jpg') || file.endsWith('.png') || file.endsWith('.jpeg'))
                    )
                ];
                
                let downloadedFile = null;
                for (const file of possibleFiles) {
                    if (fs.existsSync(file)) {
                        downloadedFile = file;
                        break;
                    }
                }
                
                if (downloadedFile) {
                    console.log(`Creator logo downloaded successfully: ${downloadedFile}`);
                    
                    // Send the file to the user
                    res.setHeader('Content-Disposition', `attachment; filename="freefbzone_logo.png"`);
                    
                    // Determine content type from file extension
                    const contentType = downloadedFile.endsWith('.png') ? 'image/png' : 'image/jpeg';
                    res.setHeader('Content-Type', contentType);
                    
                    // Stream the file to the response
                    const fileStream = fs.createReadStream(downloadedFile);
                    fileStream.pipe(res);
                    
                    // Clean up the file after sending
                    fileStream.on('end', () => {
                        try {
                            fs.unlinkSync(downloadedFile);
                            console.log(`Cleaned up temporary file: ${downloadedFile}`);
                        } catch (cleanupError) {
                            console.error(`Failed to cleanup file: ${cleanupError.message}`);
                        }
                    });
                    
                } else {
                    console.error(`Automation claimed success but no image file found`);
                    return res.status(500).json({ error: 'Image file creation failed despite successful automation.' });
                }
            } else {
                // Automation failed, extract error message
                const errorMatch = stdout.match(/❌[^\n]*/g);
                const errorMessage = errorMatch ? errorMatch[errorMatch.length - 1] : 'Unknown automation error';
                return res.status(500).json({ error: `Automation failed: ${errorMessage}` });
            }
        });
        
    } catch (error) {
        console.error('Error in /download-creator-logo-from-video endpoint:', error);
        res.status(500).json({ error: 'Download failed: An unexpected server error occurred.' });
    }
});

// New endpoint for downloading creator logo using auto_fb.py automation
app.post('/download-creator-logo-automation', async (req, res) => {
    const { profileUrl } = req.body;
    
    if (!profileUrl) {
        return res.status(400).json({ error: 'Profile URL is required' });
    }
    
    try {
        console.log(`Processing creator logo download with automation: ${profileUrl}`);
        
        // Use fixed filename for the logo
        const outputFile = 'freefbzone_logo.png';
        
        // Run auto_fb.py with the profile URL
        const command = `python auto_fb.py --profile-url "${profileUrl}" --output-file "${outputFile}"`;
        
        exec(command, { timeout: 300000 }, (error, stdout, stderr) => {
            if (error) {
                console.error(`Error executing auto_fb.py: ${error.message}`);
                return res.status(500).json({ error: 'Automation failed: An internal server error occurred.' });
            }
            
            if (stderr) {
                console.error(`auto_fb.py stderr: ${stderr}`);
            }
            
            console.log(`auto_fb.py output: ${stdout}`);
            
            // Check if automation was successful
            if (stdout.includes('AUTOMATION_SUCCESS')) {
                // Check if the file was actually created
                if (fs.existsSync(outputFile)) {
                    console.log(`Creator logo downloaded successfully: ${outputFile}`);
                    
                    // Send the file to the user
                    res.setHeader('Content-Disposition', `attachment; filename="freefbzone_logo.png"`);
                    res.setHeader('Content-Type', 'image/png');
                    
                    // Stream the file to the response
                    const fileStream = fs.createReadStream(outputFile);
                    fileStream.pipe(res);
                    
                    // Clean up the file after sending
                    fileStream.on('end', () => {
                        try {
                            fs.unlinkSync(outputFile);
                            console.log(`Cleaned up temporary file: ${outputFile}`);
                        } catch (cleanupError) {
                            console.error(`Failed to cleanup file: ${cleanupError.message}`);
                        }
                    });
                    
                } else {
                    console.error(`Automation claimed success but file not found: ${outputFile}`);
                    return res.status(500).json({ error: 'File creation failed despite successful automation.' });
                }
            } else {
                // Automation failed, extract error message
                const errorMatch = stdout.match(/❌[^\n]*/g);
                const errorMessage = errorMatch ? errorMatch[errorMatch.length - 1] : 'Unknown automation error';
                return res.status(500).json({ error: `Automation failed: ${errorMessage}` });
            }
        });
        
    } catch (error) {
        console.error('Error in /download-creator-logo-automation endpoint:', error);
        res.status(500).json({ error: 'Download failed: An unexpected server error occurred.' });
    }
});

app.listen(port, () => {
    console.log(`Server is running! Open http://localhost:${port} in your browser.`);
});
