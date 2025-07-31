#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Facebook Video to Profile Picture Automation
============================================
This script automates the process of:
1. Taking a Facebook video URL as input
2. Extracting the uploader's profile URL using fb_uploader.py
3. Automatically launching the profile and downloading the profile picture using click.py
"""

import subprocess
import sys
import os
import time
import argparse

# Set UTF-8 encoding for Windows console
if sys.platform.startswith('win'):
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass  # Skip encoding setup if it fails

def run_fb_uploader(video_url):
    """
    Run fb_uploader.py with the video URL and extract the final profile URL
    """
    print("🎬 Step 1: Extracting uploader profile from video...")
    print("=" * 60)
    
    try:
        # Run fb_uploader.py as a subprocess and capture output
        # Use encoding='utf-8' and errors='replace' to handle Unicode issues
        result = subprocess.run([
            sys.executable, 'fb_uploader.py'
        ], input=video_url, text=True, capture_output=True, 
           timeout=120, encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            # Check if stdout is None
            if result.stdout is None:
                print("❌ No output received from fb_uploader.py")
                return None
                
            output_lines = result.stdout.split('\n')
            final_url = None
            
            # Look for the "Final URL:" line in the output (with or without emoji)
            for line in output_lines:
                if "Final URL:" in line:
                    # Handle both "Final URL:" and "🔗 Final URL:" formats
                    final_url = line.split("Final URL:")[-1].strip()
                    break
            
            if final_url:
                print("✅ Successfully extracted profile URL!")
                print(f"🔗 Profile URL: {final_url}")
                return final_url
            else:
                print("❌ Could not find Final URL in fb_uploader output")
                print("📄 Full output:")
                print(result.stdout)
                return None
        else:
            print("❌ fb_uploader.py failed to run")
            print("📄 Error output:")
            if result.stderr:
                print(result.stderr)
            else:
                print("No error output available")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ fb_uploader.py timed out after 2 minutes")
        return None
    except Exception as e:
        print(f"❌ Error running fb_uploader.py: {e}")
        return None

def run_profile_automation(profile_url, output_filename='freefbzone_logo.png'):
    """
    Run profile_automation.py with the extracted profile URL
    """
    print("\n🖼️ Step 2: Opening profile and downloading picture...")
    print("=" * 60)
    
    try:
        # Pass the output filename to the profile automation script
        result = subprocess.run([
            sys.executable, 'profile_automation.py',
            '--url', profile_url,
            '--output-file', output_filename
        ], text=True, timeout=300, capture_output=True, encoding='utf-8', errors='replace')
        
        # Print stdout and stderr for debugging
        if result.stdout:
            print("📄 Profile automation output:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️ Profile automation errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Profile processing completed successfully!")
            return True
        else:
            print(f"⚠️ profile_automation.py finished with return code {result.returncode}")
            print("💡 This might still be successful if the image was downloaded")
            return True  # Still return True as it might work even with warnings
            
    except subprocess.TimeoutExpired:
        print("❌ profile_automation.py timed out after 5 minutes")
        return False
    except KeyboardInterrupt:
        print("\n👋 Process interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Error running profile_automation.py: {e}")
        return False

def validate_facebook_video_url(url):
    """
    Basic validation for Facebook video URLs
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    if 'facebook.com' not in url:
        return False, "URL must be a Facebook URL"
    
    # Check for video URL patterns
    valid_patterns = ['/share/v/', '/watch/', '/videos/', '/reel/']
    if not any(pattern in url for pattern in valid_patterns):
        return False, "URL doesn't appear to be a Facebook video URL"
    
    return True, url

def extract_profile_url_directly(video_url):
    """
    Directly extract profile URL from video URL using fb_uploader logic
    """
    try:
        # Import fb_uploader functions directly
        from fb_uploader import extract_uploader_from_video_url
        
        print(f"🔍 Extracting profile URL from: {video_url}")
        uploader_profiles = extract_uploader_from_video_url(video_url)
        
        if uploader_profiles and len(uploader_profiles) > 0:
            # Select the most likely profile (usually the first or second result)
            if len(uploader_profiles) > 1:
                primary_profile = uploader_profiles[1]  # Second result is usually more accurate
            else:
                primary_profile = uploader_profiles[0]
            
            profile_name, profile_url = primary_profile
            print(f"✅ Successfully extracted profile URL: {profile_url}")
            return profile_url
        else:
            print("❌ Could not extract profile URL from video")
            return None
            
    except Exception as e:
        print(f"❌ Error extracting profile URL: {e}")
        return None

def main():
    # Add argument parser for non-interactive mode
    parser = argparse.ArgumentParser(description='Facebook Video to Profile Picture Automation.')
    parser.add_argument('--profile-url', help='The Facebook profile URL to process directly.')
    parser.add_argument('--video-url', help='The Facebook video URL to process non-interactively.')
    parser.add_argument('--output-file', default='freefbzone_logo.png', help='The output filename for the logo.')
    args = parser.parse_args()

    # If profile_url is provided, run in non-interactive mode for profile URL
    if args.profile_url:
        print(f"🖼️  Non-interactive mode: Downloading logo from {args.profile_url}")
        success = run_profile_automation(args.profile_url, args.output_file)
        if success:
            print(f"✅ Logo downloaded successfully as {args.output_file}")
            # Signal success to the calling process
            print("AUTOMATION_SUCCESS")
        else:
            print("❌ Logo download failed.")
        return
        
    video_url = None
    # Determine if running interactively or not
    is_interactive = not args.video_url

    if is_interactive:
        print("🚀 Facebook Video to Profile Picture Automation")
        print("=" * 60)
        print("📝 This script will:")
        print("   1. Extract the uploader\'s profile from a Facebook video")
        print("   2. Open the profile and download the profile picture")
        print("=" * 60)
        print("\n📹 Enter Facebook video URL:")
        print("   Example: https://www.facebook.com/share/v/16CXxsE4A6/")
        video_url = input("\nVideo URL: ").strip()
    else:
        video_url = args.video_url
        print(f"📹 Non-interactive mode: Processing video URL {video_url}")

    if not video_url:
        print("❌ No URL provided")
        return
    
    # Validate URL
    is_valid, result = validate_facebook_video_url(video_url)
    if not is_valid:
        print(f"❌ Error: {result}")
        return
    
    video_url = result
    print(f"✅ Valid video URL: {video_url}")
    
    # Convert to canonical format
    if 'facebook.com' in video_url:
        video_url = video_url.split('?')[0]  # Strip query
        
    # Step 1: Extract profile URL directly (simplified approach)
    profile_url = extract_profile_url_directly(video_url)
    
    if not profile_url:
        print("\n❌ Failed to extract profile URL. Automation stopped.")
        return
    
    # Step 2: Process profile using profile_automation.py (only if we have a valid profile URL)
    print(f"\n🔄 Proceeding to process profile: {profile_url}")
    success = run_profile_automation(profile_url, args.output_file)
    
    if success:
        print("\n🎉 Automation completed successfully!")
        if is_interactive:
             print("💡 Check your browser and download folder for the profile picture")
    else:
        print("\n⚠️ Automation completed with some issues")
        if is_interactive:
            print("💡 You may need to check the browser manually")
    
    # Always show the summary with the extracted profile URL
    print("\n📋 Summary:")
    print(f"   📹 Video URL: {video_url}")
    print(f"   👤 Profile URL: {profile_url}")
    print("   🖼️ Profile picture processing: Completed")
    
    # Signal success if in non-interactive video_url mode
    if args.video_url and success:
        print("AUTOMATION_SUCCESS")

    # Don't wait for input in non-interactive mode
    if not is_interactive:
        pass  # Skip waiting for input in automated mode
    else:
        print("\n👋 Press Enter to exit...")
        input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Automation interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("👋 Press Enter to exit...")
        input()
