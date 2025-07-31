# Proxy-based Facebook Scraper
# Uses rotating proxies to avoid cloud platform detection

import requests
import re
import random
import time
from itertools import cycle

class FacebookProxyScraper:
    def __init__(self):
        # Your working proxies from the image
        self.proxies = [
            '23.95.150.145:6114',
            '198.23.239.134:6540',
            '45.38.107.97:6014',
            '207.244.217.165:6712',
            '107.172.163.27:6543',
            '104.222.161.211:6343',
            '64.137.96.74:6641',
            '216.10.27.159:6837',
            '136.0.207.84:6661',
            '142.147.128.93:6593'
        ]
        self.proxy_auth = ('sckfugob', '2j5x61bsrvu0')  # Username and password from your image
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
    
    def load_proxies(self):
        """Proxies are already loaded from __init__"""
        print(f"✅ Using {len(self.proxies)} pre-configured proxies")
        random.shuffle(self.proxies)
    
    def get_working_proxy(self):
        """Test and return a working proxy"""
        test_url = "http://httpbin.org/ip"
        
        for proxy in self.proxies[:20]:  # Test first 20 proxies
            try:
                proxy_dict = {
                    'http': f'http://{proxy}',
                    'https': f'http://{proxy}'
                }
                
                response = requests.get(test_url, proxies=proxy_dict, timeout=5)
                if response.status_code == 200:
                    print(f"✅ Working proxy found: {proxy}")
                    return proxy_dict
            except:
                continue
        
        print("❌ No working proxy found - running without proxy")
        return None
    
    def scrape_with_proxy(self, video_url, max_attempts=5):
        """Scrape Facebook video with proxy rotation"""
        
        for attempt in range(max_attempts):
            try:
                # Get a working proxy
                proxy_dict = self.get_working_proxy() if self.proxies else None
                
                # Random user agent
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                print(f"🔄 Attempt {attempt + 1} with {'proxy' if proxy_dict else 'direct connection'}")
                
                # Make request
                response = requests.get(
                    video_url, 
                    headers=headers, 
                    proxies=proxy_dict,
                    timeout=30,
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    print("✅ Page fetched successfully")
                    return self.extract_profiles_from_content(response.text)
                
                # Random delay between attempts
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed: {e}")
                continue
        
        return None
    
    def extract_profiles_from_content(self, content):
        """Extract profile information from page content"""
        patterns = [
            r'\"profile\.php\?id=(\d{15,})\"',
            r'href=\"https://www\.facebook\.com/profile\.php\?id=(\d{15,})\"',
            r'\"author_id\":\"(\d{15,})\"',
            r'\"owner_id\":\"(\d{15,})\"',
        ]
        
        found_ids = set()
        for pattern in patterns:
            matches = re.findall(pattern, content)
            found_ids.update(matches)
        
        if found_ids:
            profiles = []
            for profile_id in found_ids:
                profile_url = f"https://www.facebook.com/profile.php?id={profile_id}"
                profiles.append(("Unknown", profile_url))
            return profiles
        
        return None

# Usage example:
def main():
    scraper = FacebookProxyScraper()
    scraper.load_proxies()
    
    video_url = input("Enter Facebook video URL: ")
    result = scraper.scrape_with_proxy(video_url)
    
    if result:
        print("✅ Found profiles:")
        for name, url in result:
            print(f"🔗 {url}")
    else:
        print("❌ Could not extract profile information")

if __name__ == "__main__":
    main()
