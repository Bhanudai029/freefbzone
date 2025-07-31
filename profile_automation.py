import subprocess
import sys
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import urllib.parse
from urllib.parse import urlparse
import re

def download_chromedriver():
    """
    Download the correct ChromeDriver for Windows and Linux
    """
    import zipfile
    import platform
    import json
    
    # Detect platform
    current_platform = platform.system()
    if current_platform == "Windows":
        platform_name = "win64"
        driver_name = "chromedriver.exe"
        print("[DL] Downloading ChromeDriver for Windows...")
    else:
        platform_name = "linux64"
        driver_name = "chromedriver"
        print("[DL] Downloading ChromeDriver for Linux...")
    
    # Get the correct ChromeDriver version for Chrome (latest stable)
    try:
        # First, try to get the latest stable version
        version_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        response = requests.get(version_url)
        if response.status_code == 200:
            versions_data = response.json()
            # Find the latest version that has chromedriver downloads for the current platform
            target_version = None
            for version_info in reversed(versions_data['versions']):  # Start from latest
                version = version_info['version']
                if 'chromedriver' in version_info.get('downloads', {}):
                    chromedriver_downloads = version_info['downloads']['chromedriver']
                    # Look for the current platform version
                    for download in chromedriver_downloads:
                        if download['platform'] == platform_name:
                            target_version = version
                            driver_url = download['url']
                            break
                    if target_version:
                        break
            
            if not target_version:
                # Fallback to a known working version
                if current_platform == "Windows":
                    driver_url = "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.108/win64/chromedriver-win64.zip"
                else:
                    driver_url = "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.108/linux64/chromedriver-linux64.zip"
                target_version = "131.0.6778.108"
        else:
            # Fallback URLs
            if current_platform == "Windows":
                driver_url = "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.108/win64/chromedriver-win64.zip"
            else:
                driver_url = "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.108/linux64/chromedriver-linux64.zip"
            target_version = "131.0.6778.108"
    except:
        # Fallback URLs in case of any error
        if current_platform == "Windows":
            driver_url = "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.108/win64/chromedriver-win64.zip"
        else:
            driver_url = "https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.108/linux64/chromedriver-linux64.zip"
        target_version = "131.0.6778.108"
    
    print(f"[*] Using ChromeDriver version: {target_version}")
    print(f"[*] Download URL: {driver_url}")
    
    try:
        response = requests.get(driver_url)
        if response.status_code == 200:
            # Save the zip file
            zip_path = "chromedriver.zip"
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            # Extract the driver
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(".")
            
            # Clean up
            os.remove(zip_path)
            
            # The new ChromeDriver structure has nested folders
            if current_platform == "Windows":
                possible_paths = [
                    os.path.abspath("chromedriver.exe"),
                    os.path.abspath("chromedriver-win64/chromedriver.exe")
                ]
                final_path = os.path.abspath("chromedriver.exe")
                cleanup_folder = "chromedriver-win64"
            else:
                possible_paths = [
                    os.path.abspath("chromedriver"),
                    os.path.abspath("chromedriver-linux64/chromedriver")
                ]
                final_path = os.path.abspath("chromedriver")
                cleanup_folder = "chromedriver-linux64"
            
            driver_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    driver_path = path
                    break
            
            if driver_path:
                # Move it to the current directory for easier access
                if driver_path != final_path:
                    import shutil
                    shutil.move(driver_path, final_path)
                    # Clean up the extracted folder
                    try:
                        if os.path.exists(cleanup_folder):
                            shutil.rmtree(cleanup_folder)
                    except:
                        pass
                
                # Make it executable on Linux (not needed on Windows)
                if current_platform != "Windows":
                    os.chmod(final_path, 0o755)
                print(f"[OK] ChromeDriver downloaded successfully: {final_path}")
                return final_path
            else:
                print("[ERROR] Failed to extract ChromeDriver")
                return None
        else:
            print(f"[ERROR] Failed to download ChromeDriver: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Error downloading ChromeDriver: {e}")
        return None

def find_chrome_executable():
    """
    Find Chrome executable on Windows and Linux
    """
    import platform
    
    if platform.system() == "Windows":
        possible_paths = [
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
            "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
        ]
    else:
        possible_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/snap/bin/chromium",
            "/opt/google/chrome/chrome",
            "/opt/google/chrome/google-chrome"
        ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"[*] Found Chrome at: {path}")
            return path
    
    print("[ERROR] Chrome executable not found in standard locations")
    return None

def setup_webdriver():
    """
    Set up Chrome WebDriver with proper options using webdriver-manager
    """
    try:
        print("[DL] Setting up WebDriver in headless mode for production...")
        
        # Find Chrome executable
        chrome_path = find_chrome_executable()
        if not chrome_path:
            print("[ERROR] Chrome installation not found. Please install Google Chrome.")
            return None
        
        # Set up Chrome options - HEADLESS MODE ENABLED FOR PRODUCTION
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # ENABLED - for reliable background automation
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        
        # Set Chrome binary location
        chrome_options.binary_location = chrome_path
        
        # Configure download settings for headless mode
        download_dir = os.path.abspath(".")
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        print("[*] Setting up ChromeDriver...")
        # Try manual download first for better compatibility
        driver_path = download_chromedriver()
        if driver_path:
            print(f"[OK] Using manual ChromeDriver: {driver_path}")
            service = Service(driver_path)
        else:
            print("[*] Manual download failed, trying WebDriver manager...")
            try:
                service = Service(ChromeDriverManager().install())
                print("[OK] Using WebDriver manager ChromeDriver")
            except Exception as e:
                print(f"[ERROR] WebDriver manager also failed: {e}")
                print("[ERROR] Failed to setup ChromeDriver")
                return None
        
        print("[*] Creating WebDriver instance...")
        # Create WebDriver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute script to hide automation indicators
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Test the driver
        print("[*] Testing WebDriver...")
        driver.get("about:blank")
        print("[OK] WebDriver initialized successfully in headless mode")
        return driver
        
    except Exception as e:
        print(f"[ERROR] Error setting up WebDriver: {e}")
        print(f"[*] Error details: {type(e).__name__}: {str(e)}")
        return None

# Working proxy list from your provided data
WORKING_PROXIES = [
    {'proxy': '23.95.150.145:6114', 'username': 'sckfugob', 'password': '2j5x61bsrvu0'},
    {'proxy': '198.23.239.134:6540', 'username': 'sckfugob', 'password': '2j5x61bsrvu0'},
    {'proxy': '45.38.107.97:6014', 'username': 'sckfugob', 'password': '2j5x61bsrvu0'},
    {'proxy': '207.244.217.165:6712', 'username': 'sckfugob', 'password': '2j5x61bsrvu0'},
    {'proxy': '107.172.163.27:6543', 'username': 'sckfugob', 'password': '2j5x61bsrvu0'},
    {'proxy': '104.222.161.211:6343', 'username': 'sckfugob', 'password': '2j5x61bsrvu0'},
    {'proxy': '64.137.96.74:6641', 'username': 'sckfugob', 'password': '2j5x61bsrvu0'},
    {'proxy': '216.10.27.159:6837', 'username': 'sckfugob', 'password': '2j5x61bsrvu0'},
    {'proxy': '136.0.207.84:6661', 'username': 'sckfugob', 'password': '2j5x61bsrvu0'},
    {'proxy': '142.147.128.93:6593', 'username': 'sckfugob', 'password': '2j5x61bsrvu0'}
]

def get_proxy_session():
    """
    Create a requests session with a working proxy
    """
    import random
    session = requests.Session()
    
    # Try up to 3 random proxies
    for _ in range(3):
        proxy_info = random.choice(WORKING_PROXIES)
        proxy_url = f"http://{proxy_info['username']}:{proxy_info['password']}@{proxy_info['proxy']}"
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        try:
            # Test the proxy with a quick request
            test_response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
            if test_response.status_code == 200:
                print(f"[*] Using working proxy: {proxy_info['proxy']}")
                session.proxies.update(proxies)
                return session
        except:
            continue
    
    print("[WARN] All proxies failed, using direct connection")
    return session

def download_image_from_url(image_url, filename=None):
    """
    Download an image directly from its URL using working proxies
    """
    global OUTPUT_FILENAME
    try:
        if not filename:
            # Use the global output filename if available
            if 'OUTPUT_FILENAME' in globals():
                filename = OUTPUT_FILENAME
            else:
                # Generate filename from URL
                from urllib.parse import urlparse
                parsed_url = urlparse(image_url)
                filename = "downloaded_image.jpg"  # Default filename
                
                # Try to get extension from URL
                if parsed_url.path:
                    path_parts = parsed_url.path.split('.')
                    if len(path_parts) > 1:
                        ext = path_parts[-1].lower()
                        if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                            filename = f"facebook_profile_image.{ext}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
        }
        
        print(f"[*] Downloading image from: {image_url[:100]}...")
        
        # Get a session with working proxy
        session = get_proxy_session()
        response = session.get(image_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Verify it's actually an image
            content_type = response.headers.get('content-type', '')
            if 'image' in content_type.lower():
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                print(f"[OK] Image downloaded successfully: {filename} ({file_size} bytes)")
                print(f"[*] Saved to: {os.path.abspath(filename)}")
                return True
            else:
                print(f"[ERROR] URL doesn't contain image data (Content-Type: {content_type})")
                return False
        else:
            print(f"[ERROR] Failed to download image: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error downloading image: {e}")
        return False

def download_facebook_image_simple(photo_url):
    """
    Simple download approach - fetch the page HTML and extract image URLs
    """
    print("\n[DL]  Attempting to download image (simple method)...")
    
    # If the URL looks like a direct image URL, try downloading it directly
    if any(ext in photo_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
        print("[*] URL appears to be a direct image link, attempting direct download...")
        return download_image_from_url(photo_url)
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        print(f"[*] Fetching page: {photo_url}")
        response = requests.get(photo_url, headers=headers)
        
        if response.status_code == 200:
            page_content = response.text
            print("[OK] Page fetched successfully")
            
            # Look for common Facebook image URL patterns in the HTML
            import re
            
            # Enhanced patterns to find scontent image URLs (Facebook's CDN)
            # Optimized based on successful download pattern
            image_patterns = [
                # Most successful pattern from previous run - prioritize scontent URLs
                r'(https://scontent[^\s"\'>]*\.(?:jpg|jpeg|png|webp)[^\s"\'>]*)',
                r'"(https://scontent[^"]*\.(?:jpg|jpeg|png|webp)[^"]*?)"',
                r'src="(https://[^"]*scontent[^"]*\.(?:jpg|jpeg|png|webp)[^"]*?)"',
                r'href="(https://scontent[^"]*\.(?:jpg|jpeg|png|webp)[^"]*?)"',
                r'"(https://[^"]*fbcdn[^"]*\.(?:jpg|jpeg|png|webp)[^"]*?)"',
                # Additional patterns for better coverage
                r'url\(["\']?(https://scontent[^)"\'>]*\.(?:jpg|jpeg|png|webp)[^)"\'>]*)["\']?\)',
                r'background-image:[^;]*url\(["\']?(https://scontent[^)"\'>]*)["\']?\)',
            ]
            
            found_images = []
            for pattern in image_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                found_images.extend(matches)
            
            if found_images:
                # Remove duplicates and sort by URL length (longer URLs often have better quality)
                unique_images = list(set(found_images))
                # Filter out very small images (likely thumbnails or icons)
                unique_images = [img for img in unique_images if len(img) > 50]
                unique_images.sort(key=len, reverse=True)
                
                print(f"[*] Found {len(unique_images)} potential image URLs")
                
                # Based on previous success, try downloading images starting from the most promising ones
                # Previous success was with image 3, so we'll be smarter about selection
                for i, image_url in enumerate(unique_images[:7]):  # Try up to 7 images (as previous success was #3)
                    print(f"[*] Trying image {i+1}: {image_url[:80]}...")
                    
                    # Try to download the image using the global output filename
                    if 'OUTPUT_FILENAME' in globals():
                        filename = OUTPUT_FILENAME
                    else:
                        filename = f"facebook_image_{i+1}.jpg"
                    
                    success = download_image_from_url(image_url, filename)
                    if success:
                        print(f"[OK] Successfully downloaded using image URL #{i+1}")
                        return True
                    
                    # Don't give up immediately on HTTP 403, try the next ones
                    # (as we know from previous run that #3 worked when #1 and #2 failed)
                    # Continue to next image if this one fails
                    continue
                
                print("[ERROR] None of the found URLs contained downloadable images after trying all candidates")
                return False
            else:
                print("[ERROR] No image URLs found in page content")
                return False
        else:
            print(f"[ERROR] Failed to fetch page: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error during simple download: {e}")
        return False

def download_facebook_image_with_browser(photo_url):
    """
    Download Facebook image using headless browser automation
    """
    print("\n[DL]  Attempting to download image using headless browser...")
    
    try:
        # Initialize headless browser driver
        driver = setup_webdriver()
        if not driver:
            return False
        
        print(f"[*] Opening photo page: {photo_url}")
        driver.get(photo_url)
        time.sleep(5)  # Wait for page to load
        
        # Find the main image on the page
        image_selectors = [
            "img[data-visualcompletion='media-vc-image']",
            "img[style*='object-fit']",
            "div[data-pagelet='MediaViewerPhoto'] img",
            "img[src*='scontent']",
            "img[src*='fbcdn']"
        ]
        
        image_element = None
        image_url = None
        
        for selector in image_selectors:
            try:
                elements = driver.find_elements("css selector", selector)
                for element in elements:
                    src = element.get_attribute('src')
                    if src and ('scontent' in src or 'fbcdn' in src):
                        image_element = element
                        image_url = src
                        print(f"[*] Found image with selector: {selector}")
                        break
                if image_element:
                    break
            except Exception as e:
                continue
        
        if image_url:
            print(f"[IMG] Found image URL: {image_url[:100]}...")
            
            # Get browser cookies for authenticated requests
            cookies = driver.get_cookies()
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie['name']] = cookie['value']
            
            # Get user agent from browser
            user_agent = driver.execute_script("return navigator.userAgent;")
            
            driver.quit()
            
            # Download using authenticated session
            headers = {
                'User-Agent': user_agent,
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site',
                'Referer': photo_url
            }
            
            print(f"[*] Downloading image with browser session...")
            response = requests.get(image_url, headers=headers, cookies=cookie_dict, timeout=30)
            
            if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                # Use the global output filename if available
                if 'OUTPUT_FILENAME' in globals():
                    filename = OUTPUT_FILENAME
                else:
                    filename = "facebook_profile_image.jpg"
                
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                print(f"[OK] Image downloaded successfully: {filename} ({file_size} bytes)")
                print(f"[*] Saved to: {os.path.abspath(filename)}")
                return True
            else:
                print(f"[ERROR] Download failed: HTTP {response.status_code}")
                return False
        else:
            print("[ERROR] Could not find image on the page")
            driver.quit()
            return False
            
    except Exception as e:
        print(f"[ERROR] Error during headless browser download: {e}")
        if 'driver' in locals():
            driver.quit()
        return False

def download_facebook_image(photo_url):
    """
    Download the Facebook profile image - uses the proven simple method first
    """
    print("\n[DL]  Attempting to download image...")
    
    # Use the simple method first since it was successful
    print("\n[DL] Using optimized simple method (previously successful)...")
    success = download_facebook_image_simple(photo_url)
    if success:
        return True
    
    # Only try browser method as fallback if simple method fails
    print("\n[*] Simple method failed, trying browser method as fallback...")
    success = download_facebook_image_with_browser(photo_url)
    if success:
        return True
    
    print("[WARN]  All download methods failed, but you can still download manually from the browser.")
    return False

def launch_chromium_and_navigate(url):
    """
    Use browser to navigate to URL and use keyboard to access profile picture
    """
    print(f"[*] Starting browser automation...")
    print(f"[*] Navigating to: {url}")
    
    try:
        # Initialize browser driver
        driver = setup_webdriver()
        if not driver:
            return False
        
        print("[OK] Browser initialized successfully!")
        print("[*] Loading profile page...")
        
        # Navigate to the profile URL
        driver.get(url)
        time.sleep(8)  # Wait for page to fully load
        
        print("[OK] Profile page loaded!")
        
        # Use keyboard navigation to access profile picture
        print("[*] Using keyboard to navigate to profile picture...")
        time.sleep(2)

        # Create ActionChains for browser-specific keyboard input
        actions = ActionChains(driver)
        
        # Focus on the body element to ensure keyboard input goes to the page
        body = driver.find_element("tag name", "body")
        actions.click(body).perform()
        time.sleep(0.5)

        # Press ESC to close any modals/pop-ups
        print("[*] Pressing ESC to close any popups...")
        actions.send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        
        # Press TAB 7 times to navigate to profile picture
        for i in range(7):
            print(f"[*] Tab {i+1}/7")
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.5)

        # Press ENTER to open profile picture
        print("[*] Pressing Enter to open profile picture...")
        actions.send_keys(Keys.ENTER).perform()
        time.sleep(5)

        # Get new URL after keyboard interaction
        current_url = driver.current_url
        print(f"[*] URL after keyboard navigation: {current_url}")

        # Check if we successfully navigated to a photo page
        if '/photo/' in current_url:
            print("[OK] Successfully navigated to profile picture page with keyboard!")
            
            # Look for the main photo image on the photo page
            photo_selectors = [
                "img[data-visualcompletion='media-vc-image']",
                "div[data-pagelet='MediaViewerPhoto'] img",
                "img[style*='object-fit']",
                "img[src*='scontent'][width]:not([width='32']):not([width='40'])", # Exclude small thumbnails
            ]
            
            final_image_url = None
            for photo_selector in photo_selectors:
                try:
                    photo_elements = driver.find_elements("css selector", photo_selector)
                    for photo_element in photo_elements:
                        photo_src = photo_element.get_attribute('src')
                        if photo_src and 'scontent' in photo_src:
                            final_image_url = photo_src
                            print(f"[IMG] Found high-res image: {photo_src[:100]}...")
                            break
                    if final_image_url:
                        break
                except:
                    continue
            
            driver.quit()
            return True, final_image_url or current_url
        else:
            print("[WARN] Keyboard navigation didn't reach photo page")
            print(f"[*] Current URL: {current_url}")
            driver.quit()
            return False
            
    except Exception as e:
        print(f"[ERROR] Error during browser navigation: {e}")
        print(f"[*] Error details: {type(e).__name__}: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return False

def validate_facebook_url(url):
    """
    Validate if the URL is a Facebook profile URL
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    if 'facebook.com' not in url:
        return False, "URL must be a Facebook profile URL"
    
    # Check if it's a valid Facebook profile pattern
    valid_patterns = [
        '/profile.php?id=',  # Numeric ID profiles
        'facebook.com/',     # Username profiles
    ]
    
    if not any(pattern in url for pattern in valid_patterns):
        return False, "Invalid Facebook profile URL format"
    
    return True, url

def main():
    import argparse
    
    # Add argument parser for command-line usage
    parser = argparse.ArgumentParser(description='Facebook Profile Picture Downloader')
    parser.add_argument('--url', help='Facebook profile URL to process')
    parser.add_argument('--output-file', default='facebook_profile_image.jpg', help='Output filename for the downloaded image')
    args = parser.parse_args()
    
    # Store the output filename globally so download functions can use it
    global OUTPUT_FILENAME
    OUTPUT_FILENAME = args.output_file
    
    # If URL is provided via command line, use it directly
    if args.url:
        url = args.url
        print(f"Processing URL from command line: {url}")
        print(f"Output file will be: {OUTPUT_FILENAME}")
    else:
        print("[*] Facebook Profile URL Launcher")
        print("=" * 40)
        
        # Default URL if you want to test quickly
        default_url = "https://www.facebook.com/10AM02/"
        
        # Get URL from user input
        print(f"[*] Enter Facebook profile URL (or press Enter for default: {default_url}):")
        user_input = input("URL: ").strip()
        
        # Use default if no input provided
        if not user_input:
            url = default_url
            print(f"Using default URL: {url}")
        else:
            url = user_input
    
    # Validate the URL
    is_valid, result = validate_facebook_url(url)
    if not is_valid:
        print(f"[ERROR] Error: {result}")
        return
    
    url = result  # Use the normalized URL
    
    # Launch browser and perform key sequence
    result = launch_chromium_and_navigate(url)
    
    # Handle the result (could be just success boolean or tuple with URL)
    if isinstance(result, tuple):
        success, photo_url = result
    else:
        success = result
        photo_url = None
    
    if success:
        print("\n[*] Task completed!")
        
        if photo_url:
            print(f"[*] Final URL: {photo_url}")
            
            # Try to download the image - handle both photo pages and direct image URLs
            if photo_url:
                # Check if it's a direct image URL
                if any(ext in photo_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                    print("[*] Detected direct image URL, attempting download...")
                    download_success = download_image_from_url(photo_url, OUTPUT_FILENAME)
                elif '/photo/' in photo_url:
                    print("[IMG] Detected Facebook photo page, extracting image...")
                    download_success = download_facebook_image(photo_url)
                else:
                    print("[IMG] Attempting to extract image from URL...")
                    download_success = download_facebook_image(photo_url)
                    
                if download_success:
                    print(f"[OK] Image downloaded successfully as: {OUTPUT_FILENAME}")
                else:
                    print("[WARN]  Image download failed, but you can still download it manually from the browser.")
            else:
                print("[WARN]  No photo URL detected for automatic download.")
        
        print("[*] Profile picture should now be accessible")
        print("[*] Check the browser window for the profile picture")
        
        # Exit immediately when run via command line (non-interactive mode)
        if args.url:
            print("[OK] Automation completed!")
            return
        
        print("\n[*] Press Ctrl+C to exit this script")
        try:
            # Keep the script running so user can see the instructions
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] Goodbye!")
    else:
        print("\n[ERROR] Failed to launch browser. Please check your Chrome installation.")

if __name__ == "__main__":
    main()
