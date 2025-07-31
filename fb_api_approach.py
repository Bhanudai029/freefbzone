# Facebook Graph API Approach
# This is more reliable for production use

import requests
import re

def get_video_uploader_via_api(video_url, access_token):
    """
    Use Facebook Graph API to get video information
    Requires a Facebook App and access token
    """
    
    # Extract video ID from URL
    video_id = extract_video_id_from_url(video_url)
    if not video_id:
        return None
    
    # Facebook Graph API endpoint
    api_url = f"https://graph.facebook.com/v18.0/{video_id}"
    
    params = {
        'fields': 'from,created_time,description,title',
        'access_token': access_token
    }
    
    try:
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'from' in data:
                uploader_info = data['from']
                return {
                    'name': uploader_info.get('name', 'Unknown'),
                    'id': uploader_info.get('id'),
                    'url': f"https://www.facebook.com/profile.php?id={uploader_info.get('id')}"
                }
    except Exception as e:
        print(f"API Error: {e}")
    
    return None

def extract_video_id_from_url(video_url):
    """Extract video ID from Facebook URL"""
    patterns = [
        r'/share/v/([^/]+)',
        r'/watch/\?v=([^&]+)',
        r'/videos/([^/]+)',
        r'/reel/([^/]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, video_url)
        if match:
            return match.group(1)
    return None

# Usage:
# result = get_video_uploader_via_api(video_url, "YOUR_ACCESS_TOKEN")
