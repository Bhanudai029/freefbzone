# Browser-as-a-Service Solution
# Uses services like Browserless, Scrapfly, or similar

import requests
import json
import re

class BrowserServiceScraper:
    def __init__(self, service_type="browserless"):
        self.service_type = service_type
        
        # Configuration for different services
        self.configs = {
            "browserless": {
                "url": "https://chrome.browserless.io/content",
                "headers": {"Content-Type": "application/json"}
            },
            "scrapfly": {
                "url": "https://api.scrapfly.io/scrape",
                "headers": {}
            }
        }
    
    def scrape_with_browserless(self, video_url, api_key):
        """
        Use Browserless.io service for cloud scraping
        """
        payload = {
            "url": video_url,
            "options": {
                "waitFor": 3000,  # Wait 3 seconds for page to load
                "viewport": {
                    "width": 1920,
                    "height": 1080
                }
            },
            "gotoOptions": {
                "waitUntil": "networkidle2"
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        try:
            response = requests.post(
                f"https://chrome.browserless.io/content?token={api_key}",
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                content = response.text
                return self.extract_profiles_from_content(content)
            else:
                print(f"❌ Browserless error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Browserless request failed: {e}")
            return None
    
    def scrape_with_scrapfly(self, video_url, api_key):
        """
        Use Scrapfly.io service for cloud scraping
        """
        params = {
            "key": api_key,
            "url": video_url,
            "render_js": True,
            "country": "US",
            "device": "desktop",
            "wait": 3000
        }
        
        try:
            response = requests.get(
                "https://api.scrapfly.io/scrape",
                params=params,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("result", {}).get("content"):
                    content = data["result"]["content"]
                    return self.extract_profiles_from_content(content)
            else:
                print(f"❌ Scrapfly error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Scrapfly request failed: {e}")
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
    
    def scrape(self, video_url, api_key, service="browserless"):
        """Main scraping method"""
        print(f"🌐 Using {service} service...")
        
        if service == "browserless":
            return self.scrape_with_browserless(video_url, api_key)
        elif service == "scrapfly":
            return self.scrape_with_scrapfly(video_url, api_key)
        else:
            print("❌ Unsupported service")
            return None

# Usage example:
def main():
    scraper = BrowserServiceScraper()
    
    video_url = input("Enter Facebook video URL: ")
    api_key = input("Enter your browser service API key: ")
    service = input("Enter service (browserless/scrapfly): ").lower()
    
    result = scraper.scrape(video_url, api_key, service)
    
    if result:
        print("✅ Found profiles:")
        for name, url in result:
            print(f"🔗 {url}")
    else:
        print("❌ Could not extract profile information")

if __name__ == "__main__":
    main()
