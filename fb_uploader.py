# -*- coding: utf-8 -*-
import requests
import re
import sys
from urllib.parse import urlparse, parse_qs
import json
from profile_automation import download_chromedriver

# Set UTF-8 encoding for Windows console
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def extract_uploader_with_browser(video_url):
    """
    Extract uploader profile using browser automation (fallback method)
    """
    print("🌐 Using browser-based extraction (fallback method)...")
    
    try:
        # Import here to avoid dependency issues if selenium is not available
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        import time
        import platform
        import os
        
        # Detect platform and set up Chrome path
        current_platform = platform.system()
        if current_platform == "Windows":
            possible_chrome_paths = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
            ]
        else:
            possible_chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/snap/bin/chromium",
                "/opt/google/chrome/chrome",
                "/opt/google/chrome/google-chrome"
            ]
        
        chrome_path = None
        for path in possible_chrome_paths:
            if os.path.exists(path):
                chrome_path = path
                break
        
        if not chrome_path:
            print("❌ Chrome not found for browser extraction")
            return None
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        chrome_options.binary_location = chrome_path
        
        # Create WebDriver
        try:
            # Try to use manual ChromeDriver download first (more reliable for Linux)
            driver_path = download_chromedriver()
            if driver_path:
                print(f"🔧 Using manual ChromeDriver: {driver_path}")
                service = Service(driver_path)
            else:
                print("🔧 Manual download failed, trying WebDriver manager...")
                service = Service(ChromeDriverManager().install())
            
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"❌ Failed to create WebDriver: {e}")
            return None
        
        try:
            # Navigate to the video URL
            driver.get(video_url)
            time.sleep(5)  # Wait for page to load
            
            # Get page source
            page_content = driver.page_source
            
            # Extract profile information using same patterns
            profiles = extract_profiles_from_content(page_content)
            
            driver.quit()
            return profiles
            
        except Exception as e:
            print(f"❌ Browser extraction failed: {e}")
            driver.quit()
            return None
            
    except ImportError:
        print("❌ Selenium not available for browser extraction")
        return None
    except Exception as e:
        print(f"❌ Browser extraction error: {e}")
        return None

def extract_profiles_from_content(page_content):
    """
    Extract profile information from page content using regex patterns
    """
    # Multiple patterns to find uploader profile information
    uploader_patterns = [
                # Pattern 1: Look for profile.php?id= links with names
                r'"name":"([^"]+)"[^}]*"url":"(https://www\.facebook\.com/profile\.php\?id=\d+)"',
                r'"url":"(https://www\.facebook\.com/profile\.php\?id=\d+)"[^}]*"name":"([^"]+)"',
                r'href="(https://www\.facebook\.com/profile\.php\?id=\d+)"[^>]*title="([^"]+)"',
                r'title="([^"]+)"[^>]*href="(https://www\.facebook\.com/profile\.php\?id=\d+)"',
                
                # Pattern 2: Simple profile.php?id= links
                r'"(https://www\.facebook\.com/profile\.php\?id=\d+)"',
                r'href="(https://www\.facebook\.com/profile\.php\?id=\d+)"',
                
                # Pattern 3: Username-based profiles with names
                r'"name":"([^"]+)"[^}]*"url":"(https://www\.facebook\.com/[a-zA-Z0-9._-]+)"',
                r'"url":"(https://www\.facebook\.com/[a-zA-Z0-9._-]+)"[^}]*"name":"([^"]+)"',
                
                # Pattern 4: Simple username-based profiles
                r'"(https://www\.facebook\.com/[a-zA-Z0-9._-]+)"',
                r'href="(https://www\.facebook\.com/[a-zA-Z0-9._-]+)"',
                
                # Pattern 5: Look in JSON-LD or structured data
                r'"author":\s*{[^}]*"@type":\s*"Person"[^}]*"name":\s*"([^"]+)"[^}]*"url":\s*"([^"]+)"',
                r'"author":\s*{[^}]*"url":\s*"([^"]+)"[^}]*"name":\s*"([^"]+)"',
                
                # Pattern 6: Look for ownerID or similar fields with names
                r'"name":"([^"]+)"[^}]*"ownerID":"(\d+)"',
                r'"ownerID":"(\d+)"[^}]*"name":"([^"]+)"',
                r'"owner_id":"(\d+)"',
                r'"authorID":"(\d+)"',
                
                # Pattern 7: Look for profile links in meta tags
                r'<meta[^>]*property="profile:username"[^>]*content="([^"]+)"',
                r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"',
                
                # Pattern 8: Look for actor_id in Facebook's internal data
                r'"actor_id":"(\d+)"',
                r'"actorID":"(\d+)"',
                
                # Pattern 9: Look for page owner information
                r'"page_id":"(\d+)"',
                r'"pageID":"(\d+)"',
                
                # Pattern 10: Look for video uploader in data attributes
                r'data-video-uploader="([^"]+)"',
                r'data-uploader-name="([^"]+)"',
                
                # Pattern 11: Look for profile info in Facebook's internal JSON
                r'"profile_name":"([^"]+)"[^}]*"profile_id":"(\d+)"',
                r'"profile_id":"(\d+)"[^}]*"profile_name":"([^"]+)"',
            ]
            
    found_profiles = []
    
    # Search for profile patterns
    for i, pattern in enumerate(uploader_patterns):
        matches = re.findall(pattern, page_content, re.IGNORECASE)
        if matches:
            print(f"🔍 Found matches with pattern {i+1}: {len(matches)} results")
            found_profiles.extend(matches)
    
    # Clean and deduplicate results
    if found_profiles:
        unique_profiles = []
        seen = set()
        
        for profile in found_profiles:
            # Handle tuple results from some regex patterns
            if isinstance(profile, tuple):
                if len(profile) == 2:
                    # Check which one is the URL and which is the name
                    if profile[0].startswith('http') or profile[0].isdigit():
                        profile_url = profile[0]
                        profile_name = profile[1]
                    else:
                        profile_name = profile[0]
                        profile_url = profile[1]
                else:
                    profile_url = profile[0]
                    profile_name = "Unknown"
            else:
                profile_url = profile
                profile_name = "Unknown"
            
            # Convert numeric IDs to full profile URLs
            if profile_url.isdigit():
                profile_url = f"https://www.facebook.com/profile.php?id={profile_url}"
            elif not profile_url.startswith('http'):
                if profile_url.isdigit():
                    profile_url = f"https://www.facebook.com/profile.php?id={profile_url}"
                else:
                    # For username-based profiles, make sure it's not a generic term
                    # Filter out invalid characters and patterns
                    if (len(profile_url) > 3 and 
                        not any(x in profile_url.lower() for x in ['www', 'com', 'facebook', 'views', 'reactions', '&#', '|', ' ']) and
                        not re.search(r'[^a-zA-Z0-9._-]', profile_url)):  # Only allow valid username characters
                        profile_url = f"https://www.facebook.com/{profile_url}"
                    else:
                        continue  # Skip invalid usernames
            
            # Filter out invalid or generic URLs
            if (profile_url not in seen and 
                'facebook.com' in profile_url and 
                'id=0' not in profile_url and  # Filter out URLs with id=0
                not any(x in profile_url.lower() for x in ['login', 'signup', 'help', 'about', 'privacy', 'terms', 'policies', 'support']) and
                len(profile_url) > 30):  # Ensure URL is substantial
                seen.add(profile_url)
                unique_profiles.append((profile_name, profile_url))
        
        # Sort by relevance - profiles with names first, then by URL length
        unique_profiles.sort(key=lambda x: (x[0] == "Unknown", -len(x[1])))
        
        return unique_profiles
    else:
        print("❌ No uploader profile information found in page content")
        return None

def extract_uploader_from_video_url(video_url):
    """
    Extract the uploader's profile information from a Facebook video URL
    """
    print(f"🔍 Analyzing video URL: {video_url}")
    
    try:
        # Create a session for better connection management
        session = requests.Session()
        
        # Enhanced headers to better mimic real browsers and avoid cloud detection
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        session.headers.update(headers)
        
        print("📡 Fetching video page...")
        response = session.get(video_url, timeout=45, allow_redirects=True)
        
        if response.status_code == 200:
            page_content = response.text
            print("✅ Page fetched successfully")
            
            # Extract profile information using patterns
            profiles = extract_profiles_from_content(page_content)
            if profiles:
                return profiles
        else:
            print(f"❌ Failed to fetch page: HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error analyzing video URL: {e}")
        
    # Multiple fallback strategies for cloud environments like Render
    print("🔄 Simple extraction failed, trying advanced fallback methods...")
    
    # Fallback 1: Try different user agents and request methods
    fallback_attempts = [
        {
            'name': 'Mobile Browser',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate'
            }
        },
        {
            'name': 'Windows Firefox',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br'
            }
        }
    ]
    
    for attempt in fallback_attempts:
        try:
            print(f"🔄 Trying {attempt['name']} headers...")
            response = requests.get(video_url, headers=attempt['headers'], timeout=30)
            if response.status_code == 200:
                page_content = response.text
                print(f"✅ {attempt['name']} request successful")
                profiles = extract_profiles_from_content(page_content)
                if profiles:
                    print(f"✅ Profile extraction successful with {attempt['name']}")
                    return profiles
        except Exception as e:
            print(f"❌ {attempt['name']} attempt failed: {e}")
            continue
    
    # Fallback 2: Extract video ID and try direct profile approach
    video_id = extract_video_id_from_url(video_url)
    if video_id:
        print(f"🔄 Trying direct video ID approach with ID: {video_id}")
        # Try to construct potential profile URLs based on video ID patterns
        potential_ids = []
        
        # Sometimes the video ID contains encoded profile information
        if len(video_id) > 10:
            # Try to extract numeric sequences that might be profile IDs
            import re
            numeric_sequences = re.findall(r'\d{8,}', video_id)
            for seq in numeric_sequences:
                if len(seq) >= 10:  # Facebook profile IDs are typically 15+ digits
                    potential_ids.append(seq)
        
        if potential_ids:
            print(f"🔍 Found potential profile IDs: {potential_ids[:3]}")
            # Return the most likely profile ID as a constructed profile
            best_id = potential_ids[0]
            constructed_profile = f"https://www.facebook.com/profile.php?id={best_id}"
            print(f"🎯 Constructed potential profile URL: {constructed_profile}")
            return [("Unknown", constructed_profile)]
    
    # Fallback 3: Browser-based extraction (most reliable but slower)
    print("🔄 Trying browser-based extraction as final fallback...")
    return extract_uploader_with_browser(video_url)

def extract_video_id_from_url(video_url):
    """
    Extract video ID from different Facebook video URL formats
    """
    try:
        # Pattern 1: /share/v/VIDEO_ID/
        match = re.search(r'/share/v/([^/]+)', video_url)
        if match:
            return match.group(1)
        
        # Pattern 2: /watch/?v=VIDEO_ID
        match = re.search(r'/watch/\?v=([^&]+)', video_url)
        if match:
            return match.group(1)
        
        # Pattern 3: /videos/VIDEO_ID
        match = re.search(r'/videos/([^/]+)', video_url)
        if match:
            return match.group(1)
        
        # Pattern 4: /reel/VIDEO_ID
        match = re.search(r'/reel/([^/]+)', video_url)
        if match:
            return match.group(1)
        
        return None
    except:
        return None

def validate_facebook_video_url(url):
    """
    Validate if the URL is a Facebook video URL
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    if 'facebook.com' not in url:
        return False, "URL must be a Facebook URL"
    
    # Check if it's a valid Facebook video URL pattern
    valid_patterns = [
        '/share/v/',  # New share format
        '/watch/',    # Watch format  
        '/videos/',   # Direct video format
        '/reel/',     # Reel format
    ]
    
    if not any(pattern in url for pattern in valid_patterns):
        return False, "URL doesn't appear to be a Facebook video URL"
    
    return True, url

def format_profile_info(profile_name, profile_url):
    """
    Format the profile information for display
    """
    try:
        # Clean up profile name if it has encoding issues
        if profile_name != "Unknown":
            # Remove common JSON artifacts
            profile_name = profile_name.replace('\\u', ' ').replace('"', '').strip()
            # Decode common HTML entities
            profile_name = profile_name.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        
        if 'profile.php?id=' in profile_url:
            # Extract numeric ID
            match = re.search(r'id=(\d+)', profile_url)
            if match:
                user_id = match.group(1)
                if profile_name != "Unknown":
                    return f"👤 Profile Name: {profile_name}\n🆔 User ID: {user_id}\n🔗 URL: {profile_url}"
                else:
                    return f"🆔 User ID: {user_id}\n🔗 URL: {profile_url}"
        else:
            # Username-based profile
            if profile_url and 'facebook.com/' in profile_url:
                username = profile_url.split('facebook.com/')[-1].split('/')[0].split('?')[0]
                if profile_name != "Unknown":
                    return f"👤 Profile Name: {profile_name}\n📝 Username: {username}\n🔗 URL: {profile_url}"
                else:
                    return f"📝 Username: {username}\n🔗 URL: {profile_url}"
            else:
                # Fallback if profile_url is malformed
                if profile_name != "Unknown":
                    return f"👤 Profile Name: {profile_name}\n🔗 URL: {profile_url}"
                else:
                    return f"🔗 URL: {profile_url}"
    except:
        pass
    
    if profile_name != "Unknown":
        if 'id=0' not in profile_url:
            return f"👤 Profile Name: {profile_name}\n🔗 URL: {profile_url}"
        else:
            return "❌ Invalid profile detected; please check the URL."
    else:
        if 'id=0' not in profile_url:
            return f"🔗 URL: {profile_url}"
        else:
            return "❌ Invalid profile detected; please check the URL."

def main():
    print("Facebook Video Uploader Profile Detector")
    print("=" * 50)
    
    # Get video URL from user input
    print("📝 Enter Facebook video URL:")
    print("   Example: https://www.facebook.com/share/v/1axgDVeCjG/")
    print("   Or: https://www.facebook.com/watch/?v=1234567890")
    
    user_input = input("\nVideo URL: ").strip()
    
    if not user_input:
        print("❌ Error: No URL provided")
        return
    
    # Validate the URL
    is_valid, result = validate_facebook_video_url(user_input)
    if not is_valid:
        print(f"❌ Error: {result}")
        return
    
    video_url = result
    print(f"✅ Valid video URL detected")
    
    # Extract video ID for reference
    video_id = extract_video_id_from_url(video_url)
    if video_id:
        print(f"🎥 Video ID: {video_id}")
    
    print(f"\n{'='*50}")
    
    # Extract uploader information
    uploader_profiles = extract_uploader_from_video_url(video_url)
    
    if uploader_profiles and len(uploader_profiles) > 0:
        print(f"\n✅ Found {len(uploader_profiles)} potential uploader profile(s):")
        print(f"{'='*50}")
        
        # Select the second result as the primary result
        if len(uploader_profiles) > 1:
            primary_profile = uploader_profiles[1]
        else:
            primary_profile = uploader_profiles[0]
        
        for i, (name, url) in enumerate(uploader_profiles, 1):
            print(f"\n📋 Result #{i}:")
            print(format_profile_info(name, url))
        
        # Highlight the selected primary result
        print(f"\n🎯 Most likely uploader profile ↑")
        if len(uploader_profiles) > 1:
            print(f"Selected Result #{2}:")
        else:
            print(f"Selected Result #{1}:")
        print(format_profile_info(primary_profile[0], primary_profile[1]))
        
        print(f"\n{'='*50}")
        print("💡 The second result is typically the most accurate video uploader")
        
        # Display final URL
        print(f"\n🔗 Final URL: {primary_profile[1]}")
        
    else:
        print("\n❌ Could not identify the video uploader")
        print("💡 This might be due to:")
        print("   • Video privacy settings")
        print("   • Page access restrictions") 
        print("   • Video may have been deleted")
        print("   • URL format not supported")
        
        print(f"\n🔄 You can try:")
        print(f"   • Opening the URL manually: {video_url}")
        print(f"   • Checking if you're logged into Facebook")

if __name__ == "__main__":
    main()
