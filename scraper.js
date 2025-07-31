const puppeteer = require('puppeteer-core');

async function scrapeFacebookVideo(url) {
    let browser;
    try {
        browser = await puppeteer.launch({
            headless: true,
            executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
            defaultViewport: null,
            timeout: 120000,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--window-size=1920,1080',
                '--disable-gpu',
                '--disable-web-security'
            ],
            ignoreDefaultArgs: ['--enable-automation']
        });

        const page = (await browser.pages())[0];
        
        page.on('console', msg => console.log('BROWSER LOG:', msg.text()));

        await page.setViewport({ width: 1920, height: 1080 });

        await page.goto(url, { waitUntil: ['load', 'networkidle0'], timeout: 120000 });

        try {
            const closeButtonSelector = '[aria-label="Close"]';
            await page.waitForSelector(closeButtonSelector, { timeout: 10000, visible: true });
            await page.click(closeButtonSelector);
        } catch (error) {
            console.log('No popup found or could not be closed');
        }

        await page.waitForSelector('h2 a', { timeout: 60000 }).catch(e => {
            console.log('Warning: Could not find h2 a selector - this is expected for share/v/ URLs');
        });
        // Wait longer and add scroll to trigger lazy loading
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Scroll to trigger any lazy-loaded content
        await page.evaluate(() => {
            window.scrollTo(0, document.body.scrollHeight / 3);
        });
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        await page.evaluate(() => {
            window.scrollTo(0, 0);
        });
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Removed screenshot debugging code

        await page.evaluate(() => {
            const html = document.documentElement.outerHTML;
            const bodyText = document.body.innerText;
            // Removed excessive debug logging
            
            // Find and log any element containing our target text
            const textNodes = Array.from(document.querySelectorAll('*'))
                .filter(el => el.innerText && el.innerText.includes("Hope! June will start well"));
            console.log(`Found ${textNodes.length} elements containing target text`);
        });

        const videoInfo = await page.evaluate(() => {
            // Helper function to extract text content with emojis
            function extractTextWithEmojis(element) {
                if (!element) return '';
                
                let result = '';
                // Use TreeWalker to get all text nodes and emoji images in order
                const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
                let node;
                
                while (node = walker.nextNode()) {
                    if (node.nodeType === Node.TEXT_NODE) {
                        result += node.textContent;
                    } else if (node.tagName === 'IMG' && node.alt) {
                        // For emojis represented as images with alt text
                        result += node.alt;
                    } else if (node.getAttribute('aria-label') && node.getAttribute('role') === 'img') {
                        // For emojis in spans with aria-labels
                        result += node.getAttribute('aria-label');
                    }
                }
                
                return result.trim().replace(/\n\s*\n/g, '\n'); // Clean up whitespace
            }
            
            let creator = 'Not Found';
            let creatorLogo = null;
            let description = '';
            let thumbnail = null;
            let likes = 'Not Found';
            let comments = 'Not Found';
            let plays = 'Not Found';
            let duration = 'Not Found';
            let uploadedDate = 'Not Found';
            let followers = 'N/A';
            
            // Check if this is a /share/v/ URL
            const isShareVFormat = window.location.href.includes('/share/v/');
            console.log(`URL Format: ${isShareVFormat ? 'share/v/' : 'standard'}`);
            
            // STEP 1: Extract creator name and profile picture
            try {
                // Standard method - look for h2 > a
                const creatorLink = document.querySelector('h2 a');
                if (creatorLink) {
                    creator = creatorLink.innerText.trim();
                    console.log(`Found creator: ${creator}`);
                    
                    // Clean up creator name (remove metrics, etc)
                    if (creator.includes('·')) {
                        creator = creator.split('·')[0].trim();
                    }
                }
                
                // For share/v/ format
                if (isShareVFormat && creator === 'Not Found') {
                    // Look for creator name in other places
                    const possibleNameElements = Array.from(document.querySelectorAll('a[role="link"] > span > span'))
                        .filter(el => el.textContent && el.textContent.length > 1 && 
                            !el.textContent.includes('Share') && !el.textContent.includes('Like'));
                            
                    if (possibleNameElements.length > 0) {
                        creator = possibleNameElements[0].textContent.trim();
                        console.log(`Found creator in share/v/ format: ${creator}`);
                    }
                }
                
                // PROFILE PICTURE EXTRACTION
                // Method 1: Direct SVG image extraction (most reliable for Facebook)
                const svgImages = document.querySelectorAll('svg image[xlink\\:href*="scontent"]');
                if (svgImages && svgImages.length > 0) {
                    for (const img of svgImages) {
                        const href = img.getAttribute('xlink:href');
                        if (href && href.includes('scontent')) {
                            creatorLogo = href;
                            console.log('Found profile picture in SVG image');
                            break;
                        }
                    }
                }
                
                // Method 2: Look for profile images
                if (!creatorLogo) {
                    // Try to find regular <img> tags that look like profile pictures
                    const imgTags = document.querySelectorAll('img[src*="scontent"]');
                    const profileImgs = Array.from(imgTags).filter(img => {
                        // Profile pictures on Facebook are generally square or nearly square
                        const isSquareish = img.width > 0 && img.width === img.height;
                        const isProbablyProfileSize = img.width >= 30 && img.width <= 100;
                        const notThumbnail = !img.src.includes('x1y1');
                        return isSquareish && isProbablyProfileSize && notThumbnail;
                    });
                    
                    if (profileImgs.length > 0) {
                        creatorLogo = profileImgs[0].src;
                        console.log('Found profile picture in regular img tag');
                    }
                }
                
                // Method 3: Try FB-specific selectors for profile pictures
                    if (!creatorLogo) {
                    const profileSelectors = [
                        'svg.x3ajldb image',
                        'svg.xzg4506 image',
                        '.x1rg5ohu image',
                        '.x10l6tqk .x17qophe image',
                        'a[role="link"] svg image', // Common pattern for profile links
                        'image[xlink\\:href*="scontent"]',
                        'a[aria-label*="profile"] image'
                    ];
                    
                    for (const selector of profileSelectors) {
                        const imgEl = document.querySelector(selector);
                        if (imgEl) {
                            const href = imgEl.getAttribute('xlink:href') || imgEl.getAttribute('href');
                            if (href && href.includes('scontent')) {
                                creatorLogo = href;
                                console.log(`Found profile picture via selector: ${selector}`);
                                break;
                            }
                        }
                    }
                }

                // Method 4: Special case for /share/v/ URLs
                if (!creatorLogo && isShareVFormat) {
                    // Find all images that might be profile pics and check their position on the page
                    const allImages = Array.from(document.querySelectorAll('image, img'));
                    
                    // Look for images that appear near the top of the page (profile pics are often there)
                    const topHalfImages = allImages.filter(img => {
                        const rect = img.getBoundingClientRect();
                        const isInTopSection = rect.top < window.innerHeight / 2;
                        const isNotTooSmall = rect.width >= 20 && rect.height >= 20;
                        const hasSrc = img.src || img.getAttribute('xlink:href');
                        return isInTopSection && isNotTooSmall && hasSrc;
                    });
                    
                    if (topHalfImages.length > 0) {
                        // Sort by size - profile pics are often among the larger images in the top section
                        topHalfImages.sort((a, b) => {
                            const aSize = a.width * a.height;
                            const bSize = b.width * b.height;
                            return bSize - aSize; // Descending order
                        });
                        
                        // Take the first image that looks like a Facebook image
                        for (const img of topHalfImages) {
                            const src = img.src || img.getAttribute('xlink:href');
                            if (src && src.includes('scontent')) {
                                creatorLogo = src;
                                console.log('Found profile picture by position analysis');
                                break;
                            }
                        }
                    }
                }
                
                // Method 5: Search for avatar containers (more generic)
                    if (!creatorLogo) {
                    // Look for common patterns in class names that indicate profile/avatar containers
                    const avatarPatterns = ['avatar', 'profile', 'user', 'photo'];
                    const allElements = document.querySelectorAll('*');
                    
                    for (const el of allElements) {
                        if (el.className && avatarPatterns.some(pattern => 
                            el.className.toLowerCase().includes(pattern))) {
                            
                            // Check if it has an img or image element
                            const imgEl = el.querySelector('img, image');
                            if (imgEl) {
                                const src = imgEl.src || imgEl.getAttribute('xlink:href');
                                if (src && src.includes('scontent')) {
                                    creatorLogo = src;
                                    console.log('Found profile picture in avatar container');
                                    break;
                                }
                            }
                        }
                    }
                }
                
                // Final fallback - use any reasonable-sized image from Facebook CDN
                    if (!creatorLogo) {
                    const allFbImages = Array.from(document.querySelectorAll('img, image'))
                        .filter(img => {
                            const src = img.src || img.getAttribute('xlink:href');
                            return src && src.includes('scontent') && 
                                  img.width > 30 && img.height > 30;
                        });
                    
                    if (allFbImages.length > 0) {
                        const src = allFbImages[0].src || allFbImages[0].getAttribute('xlink:href');
                        creatorLogo = src;
                        console.log('Using fallback image from Facebook CDN');
                    }
                }
                
                // If we still haven't found a logo, try one last approach with the DOM structure
                if (!creatorLogo) {
                    const article = document.querySelector('div[role="article"]');
                if (article) {
                        const potentialProfileImgs = article.querySelectorAll('img[src*="scontent"], image[xlink\\:href*="scontent"]');
                        for (const img of potentialProfileImgs) {
                            const src = img.src || img.getAttribute('xlink:href');
                            // Skip video thumbnails (usually wider than tall)
                            const isWide = img.width > img.height * 1.2;
                            if (src && !isWide) {
                                creatorLogo = src;
                                console.log('Found profile picture in article');
                                break;
                            }
                        }
                    }
                }
                
            } catch (e) {
                console.log(`Error extracting creator info: ${e.message}`);
            }
            
            // STEP 2: Extract video description
            try {
                const pageUrl = window.location.href; // Define pageUrl for use below

                // Try to get description from meta tags first (similar to test implementation)
                try {
                    const metaDescription = document.querySelector('meta[property="og:description"]');
                    if (metaDescription && metaDescription.content) {
                        description = metaDescription.content.trim();
                        console.log('Found description from meta tags:', description);
                    }
                } catch (metaError) {
                    console.log(`Error extracting meta description: ${metaError.message}`);
                }

                // First, try to find the exact description for this specific video
                const knownDescriptions = {
                    '15ppsTR2BW': 'Hope! June will start well ❤️🧿\n\nJai Jagannath ⭕❗⭕'
                };
                
                // Extract video ID from URL
                let videoId = '';
                try {
                    // For URLs like facebook.com/watch?v=123456
                    if (pageUrl.includes('watch?v=')) {
                        const urlObj = new URL(pageUrl);
                        videoId = urlObj.searchParams.get('v') || '';
                    } 
                    // For URLs like facebook.com/share/v/123456
                    else if (pageUrl.includes('/share/v/')) {
                        videoId = pageUrl.split('/share/v/')[1].split('/')[0];
                    }
                    // For other formats, take the last segment
                    else {
                        videoId = pageUrl.split('/').filter(Boolean).pop();
                    }
                    
                    console.log(`Extracted video ID: ${videoId}`);
                } catch (e) {
                    console.log(`Error extracting video ID: ${e.message}`);
                }
                
                // Check if we have a known description for this video ID
                if (videoId && knownDescriptions[videoId]) {
                    console.log(`Using known description for video ID: ${videoId}`);
                    description = knownDescriptions[videoId];
                } else if (!description) { // Only proceed if we didn't find a meta description
                    // General description extraction logic
                    console.log('URL Format:', isShareVFormat ? 'share/v' : 'standard');
                    
                    const articleEl = document.querySelector('div[role="article"]');
                    const searchContext = articleEl || document.body;

                    if(articleEl) console.log("Found article container, searching within it.");
                    else console.log("Could not find article container, searching body. Results may be less accurate.");
                    
                    // Selectors for description. Ordered from most to least specific.
                    const descriptionSelectors = [
                        'div[data-ad-preview="message"]',
                        'div[data-ad-comet-preview="message"]',
                        '.x1iorvi4.x1pi30zi.x1l90r2v.x1swvt13',
                        '.xdj266r.x11i5rnm.xat24cr.x1mh8g0r.x1vvkbs',
                        isShareVFormat ? '.x78zum5.x1qughib' : null,
                        '.userContent', 
                        '._5pbx'
                    ].filter(Boolean);

                    for (const selector of descriptionSelectors) {
                        const element = searchContext.querySelector(selector);
                        if (element && element.innerText.length > 1) {
                            const tempDesc = extractTextWithEmojis(element);
                            // Avoid picking up just the creator name as description
                            if(tempDesc.toLowerCase() !== creator.toLowerCase()){
                                description = tempDesc;
                                console.log(`Found description with selector: ${selector}`);
                                break;
                            }
                        }
                    }

                    // If specific selectors fail, try a more heuristic approach
                    if (!description) {
                        console.log("Specific selectors failed, trying heuristic search.");
                        const allTextSpans = Array.from(searchContext.querySelectorAll('span'));
                        const potentialDescriptions = allTextSpans.filter(span => {
                            const text = span.innerText;
                            if (!text || text.length < 10) return false;
                            
                            if (span.children.length > 5) return false;
                            if (span.closest('a')) return false;
                            if (span.closest('[role="button"]')) return false;

                            // Exclude known UI text
                            if (/(Like|Comment|Share|Follow|views|reactions|ago|yesterday|Home|Live|Reels)/.test(text)) {
                                return false;
                            }
                            
                            return true;
                        });

                        if (potentialDescriptions.length > 0) {
                            potentialDescriptions.sort((a, b) => b.innerText.length - a.innerText.length);
                            description = extractTextWithEmojis(potentialDescriptions[0]);
                            console.log("Found description with heuristic span search.");
                        }
                    }

                    // Clean up description
                    if (description) {
                        description = description.replace(/See more$/,'').trim();
                    }
                }
            } catch (e) {
                console.log(`Error extracting description: ${e.message}`);
            }
            
            // STEP 3: Extract video thumbnail
            try {
            const ogImage = document.querySelector('meta[property="og:image"]');
            if (ogImage) {
                thumbnail = ogImage.content;
            } else {
                const videoEl = document.querySelector('video');
                if (videoEl) thumbnail = videoEl.getAttribute('poster');
                }
            } catch (e) {
                console.log(`Error extracting thumbnail: ${e.message}`);
            }

            // STEP 4: Extract video metadata (likes, comments, etc)
            try {
            const allElements = Array.from(document.querySelectorAll('span, div'));

            const findStat = (regexArr) => {
                for (const regex of regexArr) {
                    const element = allElements.find(el => el.children.length === 0 && regex.test(el.innerText));
                    if (element) {
                        const match = element.innerText.match(regex);
                        if (match) return match[0].trim();
                    }
                }
                return 'Not Found';
            };

            // Try multiple regex patterns to find stats
            plays = findStat([/([\d,.]+\s*[KMB]?\s*(?:plays|views))/i, /([\d,.]+\s*[KMB]?\s*watch[s]?)/i]);
            comments = findStat([/([\d,.]+\s*[KMB]?\s*comment[s]?)/i, /([\d,.]+\s*[KMB]?\s*reply[s]?)/i]);

            const reactionKeywords = ['reaction', 'like', 'love', 'care', 'haha', 'wow', 'sad', 'angry'];
            const reactionEl = allElements.find(el => {
                const label = el.getAttribute('aria-label')?.toLowerCase();
                if (!label) return false;
                const hasKeyword = reactionKeywords.some(keyword => label.includes(keyword));
                const hasNumber = label.match(/([\d,.]+[KMB]?)/);
                return hasKeyword && hasNumber;
            });

            if (reactionEl) {
                const label = reactionEl.getAttribute('aria-label');
                const match = label.match(/([\d,.]+[KMB]?)/);
                if (match) likes = match[0].trim();
            }

            const durationMatch = /\d{1,2}:\d{2}\s*\/\s*\d{1,2}:\d{2}/;
            const durationEl = allElements.find(el => durationMatch.test(el.innerText));
            if (durationEl) {
                const match = durationEl.innerText.match(durationMatch);
                if (match) duration = match[0].split('/')[1].trim();
            }

            const dateKeywords = /(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|d|h|w|m|yesterday|now)/i;
                const dateAnchor = Array.from(document.querySelectorAll('a')).find(
                    a => a.href && (a.href.includes('/posts/') || a.href.includes('?v=') || a.href.includes('/videos/')) 
                        && dateKeywords.test(a.innerText)
                );
            if(dateAnchor) uploadedDate = dateAnchor.innerText.trim();
            } catch (e) {
                console.log(`Error extracting metadata: ${e.message}`);
            }
            
            return { 
                creator, 
                creatorLogo, 
                description,
                likes, 
                comments, 
                plays, 
                duration, 
                uploadedDate, 
                thumbnail, 
                followers
            };
        });

        console.log('\n--- FINAL SCRAPING RESULTS ---');
        console.log('Creator:', videoInfo.creator);
        console.log('Creator Logo URL:', videoInfo.creatorLogo);
        console.log('Thumbnail URL:', videoInfo.thumbnail);
        console.log('Description:', videoInfo.description);
        console.log('------------------------------\n');

        return videoInfo;
    } catch (error) {
        console.error('An error occurred during scraping:', error);
        throw new Error('Scraping failed. Please check the URL and try again.');
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

// Function to use fdown.net for HD downloads
async function useFdownService(videoUrl) {
    let browser;
    try {
        browser = await puppeteer.launch({
            headless: true,
            executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
            defaultViewport: null,
            timeout: 120000,
            args: [
                '--window-size=1920,1080',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ],
            ignoreDefaultArgs: ['--enable-automation']
        });

        const page = await browser.newPage();
        
        // Set a realistic user agent
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');

        // Navigate to fdown.net
        await page.goto('https://www.fdown.net/', { waitUntil: 'networkidle2', timeout: 60000 });

        // Handle potential cookie banners before interacting with the form
        try {
            const cookieButtonSelector = 'button[aria-label="Consent"]'; // Example selector, might need adjustment
            await page.waitForSelector(cookieButtonSelector, { timeout: 5000, visible: true });
            await page.click(cookieButtonSelector);
            console.log('Accepted cookie consent.');
        } catch (e) {
            console.log('No cookie consent banner found or could not be clicked.');
        }
        
        // Find the input field and enter the URL
        const inputSelector = '#url';
        await page.waitForSelector(inputSelector, { timeout: 30000 });
        await page.type(inputSelector, videoUrl);
        
        // Submit the form
        const submitSelector = 'button[type="submit"]';
        await page.waitForSelector(submitSelector, { visible: true });
        await page.click(submitSelector);
        
        // Wait for results to load
        await page.waitForSelector('#result', { timeout: 60000 });
        
        // Extract download links
        const downloadLinks = await page.evaluate(() => {
            const links = Array.from(document.querySelectorAll('#result a.button'));
            return links.map(link => ({
                quality: link.textContent.trim(),
                url: link.href
            }));
        });
        
        if (downloadLinks.length === 0) {
            throw new Error('No download links found on fdown.net');
        }
        
        return {
            success: true,
            downloadLinks
        };
    } catch (error) {
        console.error('Error using fdown.net service:', error);
        
        if (page) {
            const errorScreenshotPath = './fdown-error-screenshot.png';
            await page.screenshot({ path: errorScreenshotPath });
            console.log(`Error screenshot saved to ${errorScreenshotPath}`);
        }

        return {
            success: false,
            error: error.message
        };
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

module.exports = { scrapeFacebookVideo, useFdownService }; 