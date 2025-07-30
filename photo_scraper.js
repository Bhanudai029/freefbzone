const puppeteer = require('puppeteer');
const fetch = require('node-fetch');

async function scrapeFacebookPhoto(url) {
    let browser;
    try {
        browser = await puppeteer.launch({
            headless: true, // Set to true for faster execution
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        });

        const page = await browser.newPage();
        
        // Set viewport to ensure we get desktop version
        await page.setViewport({ width: 1920, height: 1080 });
        
        // Set user agent to appear as a real browser
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

        // Intercept network requests to capture image URLs
        const capturedUrls = new Set();
        await page.setRequestInterception(true);
        
        page.on('request', (request) => {
            const reqUrl = request.url();
            if (reqUrl.includes('fbcdn.net') && (reqUrl.includes('.jpg') || reqUrl.includes('.png') || reqUrl.includes('.webp'))) {
                console.log(`Captured network request: ${reqUrl}`);
                capturedUrls.add(reqUrl);
            }
            request.continue();
        });

        console.log(`Navigating to ${url}`);
        await page.goto(url, { 
            waitUntil: 'networkidle0',
            timeout: 45000 
        });

        // Wait for images to load
        await page.waitForTimeout(5000);

        // Try to find and click on the main image to open full view
        try {
            // Try multiple selectors for the main image
            const imageSelectors = [
                'img[data-visualcompletion="media-vc-image"]',
                'img[style*="cursor: pointer"]',
                'img[width="500"], img[height="500"]',
                'img[src*="fbcdn.net"]:not([width="16"]):not([height="16"])'
            ];
            
            for (const selector of imageSelectors) {
                try {
                    const element = await page.$(selector);
                    if (element) {
                        console.log(`Clicking on image with selector: ${selector}`);
                        await element.click();
                        await page.waitForTimeout(3000);
                        break;
                    }
                } catch (e) {
                    console.log(`Failed to click with selector ${selector}:`, e.message);
                }
            }
        } catch (e) {
            console.log('Could not click on main image');
        }

        // Scroll to load more content
        await page.evaluate(() => {
            window.scrollTo(0, document.body.scrollHeight);
        });
        await page.waitForTimeout(2000);

        // Extract all possible image URLs from the page
        const pageImageUrls = await page.evaluate(() => {
            const urls = new Set();
            
            // Method 1: All img elements
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                if (img.src && img.src.includes('fbcdn.net')) {
                    urls.add(img.src);
                }
                // Also check data attributes
                ['data-src', 'data-original', 'data-lazy-src'].forEach(attr => {
                    const dataSrc = img.getAttribute(attr);
                    if (dataSrc && dataSrc.includes('fbcdn.net')) {
                        urls.add(dataSrc);
                    }
                });
            });

            // Method 2: Background images
            const allElements = document.querySelectorAll('*');
            allElements.forEach(el => {
                const bg = window.getComputedStyle(el).backgroundImage;
                if (bg && bg.includes('fbcdn.net')) {
                    const matches = bg.match(/url\(["']?([^"'\)]+)["']?\)/g);
                    if (matches) {
                        matches.forEach(match => {
                            const url = match.replace(/url\(["']?([^"'\)]+)["']?\)/, '$1');
                            if (url.includes('fbcdn.net')) {
                                urls.add(url);
                            }
                        });
                    }
                }
            });

            // Method 3: Check all script tags for image URLs
            const scripts = document.querySelectorAll('script');
            scripts.forEach(script => {
                if (script.innerHTML) {
                    const matches = script.innerHTML.match(/https:\/\/[^"\s]*fbcdn\.net[^"\s]*\.(jpg|png|webp)/g);
                    if (matches) {
                        matches.forEach(url => urls.add(url));
                    }
                }
            });

            // Method 4: Look in JSON-LD or other structured data
            const jsonScripts = document.querySelectorAll('script[type="application/json"], script[type="application/ld+json"]');
            jsonScripts.forEach(script => {
                try {
                    const content = script.innerHTML;
                    const matches = content.match(/https:\/\/[^"\s]*fbcdn\.net[^"\s]*\.(jpg|png|webp)/g);
                    if (matches) {
                        matches.forEach(url => urls.add(url));
                    }
                } catch (e) {
                    // Ignore JSON parse errors
                }
            });

            return Array.from(urls);
        });

        console.log(`Found ${pageImageUrls.length} image URLs from page evaluation`);
        console.log(`Found ${capturedUrls.size} image URLs from network interception`);

        // Combine all URLs
        const allUrls = [...new Set([...pageImageUrls, ...Array.from(capturedUrls)])];
        
        // Generate high-quality variants for each URL
        const highQualityUrls = [];
        
        allUrls.forEach(originalUrl => {
            highQualityUrls.push(originalUrl); // Original first
            
            // Extract photo ID patterns and generate HD variants
            const patterns = [
                // Pattern 1: Standard Facebook photo format
                /\/([0-9]+_[0-9]+_[0-9]+_[a-z])\.(jpg|png|webp)/,
                // Pattern 2: Newer format
                /\/([0-9]+_[0-9]+_[0-9]+_[0-9]+_[a-z])\.(jpg|png|webp)/,
                // Pattern 3: Simple numeric ID
                /\/([0-9]{10,})\.(jpg|png|webp)/
            ];
            
            patterns.forEach(pattern => {
                const match = originalUrl.match(pattern);
                if (match) {
                    const [, photoId, ext] = match;
                    const baseUrl = originalUrl.substring(0, originalUrl.lastIndexOf('/') + 1);
                    
                    // Generate all possible quality variants
                    const qualitySuffixes = ['_o', '_b', '_n', '_t'];
                    const resolutions = ['p2048x2048', 'p1080x1080', 'p960x960', 'p720x720'];
                    
                    qualitySuffixes.forEach(suffix => {
                        highQualityUrls.push(`${baseUrl}${photoId}${suffix}.${ext}`);
                        
                        // Also try with resolution prefixes
                        resolutions.forEach(res => {
                            const resUrl = originalUrl.replace(/\/([^\/]+)$/, `/${res}/$1`);
                            highQualityUrls.push(resUrl.replace(/(_[a-z])?\.(jpg|png|webp)/, `${suffix}.$2`));
                        });
                    });
                }
            });
            
            // Try different CDN endpoints
            if (originalUrl.includes('scontent')) {
                const cdnVariants = [
                    originalUrl.replace(/scontent[^.]*\./, 'scontent.xx.'),
                    originalUrl.replace(/scontent[^.]*\./, 'scontent-lax3-1.'),
                    originalUrl.replace(/scontent[^.]*\./, 'external.')
                ];
                highQualityUrls.push(...cdnVariants);
            }
        });

        // Remove duplicates and return
        const uniqueUrls = [...new Set(highQualityUrls)];
        console.log(`Generated ${uniqueUrls.length} total URL variants to try`);

        return {
            success: true,
            imageUrls: uniqueUrls,
            originalUrl: url
        };

    } catch (error) {
        console.error('Error scraping Facebook photo:', error);
        return {
            success: false,
            error: error.message,
            imageUrls: []
        };
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

module.exports = { scrapeFacebookPhoto };
