import requests
import os
import tempfile
import sys
from pathlib import Path

# Fix Windows console encoding issues
if sys.platform == "win32":
    try:
        import codecs
        # Only set encoding if not already set
        if hasattr(sys.stdout, 'detach') and not hasattr(sys.stdout, '_wrapped'):
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
            sys.stdout._wrapped = True
        if hasattr(sys.stderr, 'detach') and not hasattr(sys.stderr, '_wrapped'):
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
            sys.stderr._wrapped = True
    except:
        pass  # If encoding setup fails, continue with default encoding

# Function to download video using Snapsave
def download_from_snapsave(video_url):
    """Wrapper function that calls the async snapsave downloader and saves the file locally"""
    import asyncio
    from snapsave_downloader import download_facebook_video_snapsave
    
    try:
        print("Starting video download...")
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(download_facebook_video_snapsave(video_url))
        
        if not result['success']:
            raise Exception(f"SnapSave failed: {result['error']}")
        
        download_url = result['download_url']
        print("Download URL obtained, downloading video file...")
        
        # Now download the file from the URL
        import requests
        import tempfile
        
        response = requests.get(download_url, stream=True, timeout=120)
        response.raise_for_status()
        
        # Create a temporary file for the video
        temp_dir = tempfile.gettempdir()
        video_file_path = os.path.join(temp_dir, f"freefbzone_video_{os.getpid()}.mp4")
        
        with open(video_file_path, 'wb') as video_file:
            for chunk in response.iter_content(chunk_size=8192):
                video_file.write(chunk)
        
        print(f"Video downloaded successfully: {os.path.basename(video_file_path)}")
        return video_file_path
        
    except Exception as e:
        raise Exception(f"Failed to download video: {str(e)}")

def download_video(video_url):
    try:
        # Use our local download_from_snapsave function
        video_file_path = download_from_snapsave(video_url)
        return video_file_path
    except Exception as e:
        raise Exception(f"Failed to download video: {str(e)}")

# Function to convert video to audio using FFmpeg (local conversion)
def convert_video_to_audio_local(video_file_path):
    try:
        import subprocess
        
        # Create a temporary file for the audio
        temp_dir = tempfile.gettempdir()
        audio_file_path = os.path.join(temp_dir, f"freefbzone_audio_{os.getpid()}.mp3")
        
        print("Converting video to audio using FFmpeg...")
        
        # FFmpeg command to convert video to MP3 with reduced verbosity
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', video_file_path,  # Input video file
            '-vn',  # No video
            '-acodec', 'libmp3lame',  # MP3 codec
            '-ab', '192k',  # Audio bitrate
            '-ar', '44100',  # Audio sample rate
            '-y',  # Overwrite output file
            '-loglevel', 'error',  # Reduce FFmpeg verbosity
            audio_file_path  # Output audio file
        ]
        
        # Execute FFmpeg command
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg conversion failed: {result.stderr}")
        
        if not os.path.exists(audio_file_path):
            raise Exception("Audio file was not created")
        
        print(f"Audio conversion completed: {os.path.basename(audio_file_path)}")
        return audio_file_path
        
    except FileNotFoundError:
        raise Exception("FFmpeg not found. Please install FFmpeg and add it to your PATH")
    except subprocess.TimeoutExpired:
        raise Exception("Conversion timeout - video file might be too large")
    except Exception as e:
        raise Exception(f"Local conversion failed: {str(e)}")

# Function to upload the video to the conversion site and download audio
def convert_video_to_audio(video_file_path):
    try:
        import time
        
        # Create a temporary file for the audio
        temp_dir = tempfile.gettempdir()
        audio_file_path = os.path.join(temp_dir, f"freefbzone_audio_{os.getpid()}.mp3")
        
        print("Uploading video to conversion service...")
        
        # Step 1: Upload video to conversion service
        upload_url = 'https://videotomp3.onrender.com/upload'
        
        with open(video_file_path, 'rb') as video_file:
            files = {'file': ('video.mp4', video_file, 'video/mp4')}
            upload_response = requests.post(upload_url, files=files, timeout=180)
        
        if upload_response.status_code != 200:
            raise Exception(f"Upload failed with status {upload_response.status_code}: {upload_response.text}")
        
        # Parse upload response to get job_id
        try:
            upload_data = upload_response.json()
            job_id = upload_data.get('job_id')
            if not job_id:
                raise Exception("No job_id received from upload response")
        except Exception as e:
            raise Exception(f"Failed to parse upload response: {str(e)}")
        
        print(f"Upload successful! Processing conversion...")
        
        # Step 2: Poll for conversion status
        status_url = f'https://videotomp3.onrender.com/status/{job_id}'
        max_attempts = 60  # Wait up to 5 minutes (60 * 5 seconds)
        attempt = 0
        
        while attempt < max_attempts:
            try:
                status_response = requests.get(status_url, timeout=30)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get('status', 'unknown')
                    
                    if status == 'completed':
                        print("Conversion completed! Downloading audio...")
                        break
                    elif status == 'failed':
                        error_msg = status_data.get('error', 'Unknown conversion error')
                        raise Exception(f"Conversion failed: {error_msg}")
                    elif status in ['processing', 'pending']:
                        if attempt % 6 == 0:  # Print status every 30 seconds (6 * 5 seconds)
                            print(f"Converting... ({attempt * 5}s elapsed)")
                        time.sleep(5)  # Wait 5 seconds before next check
                    else:
                        time.sleep(5)
                else:
                    time.sleep(5)
                    
            except requests.exceptions.RequestException as e:
                if attempt % 6 == 0:  # Print error every 30 seconds
                    print(f"Connection issue, retrying... ({attempt * 5}s elapsed)")
                time.sleep(5)
            
            attempt += 1
        
        if attempt >= max_attempts:
            raise Exception("Conversion timeout - took longer than expected")
        
        # Step 3: Download the converted MP3 file
        download_url = f'https://videotomp3.onrender.com/download/{job_id}'
        print("Downloading converted audio...")
        
        download_response = requests.get(download_url, timeout=120, stream=True)
        
        if download_response.status_code != 200:
            raise Exception(f"Download failed with status {download_response.status_code}")
        
        # Save the MP3 file
        with open(audio_file_path, 'wb') as audio_file:
            for chunk in download_response.iter_content(chunk_size=8192):
                if chunk:
                    audio_file.write(chunk)
        
        print(f"Audio saved: {os.path.basename(audio_file_path)}")
        return audio_file_path
        
    except Exception as e:
        raise Exception(f"Failed to convert video to audio: {str(e)}")

# Main function to execute the steps
def main(video_url):
    try:
        print(f"[MUSIC] Starting audio extraction from: {video_url[:50]}...")
        
        # Step 1: Download video
        print("[DOWNLOAD] Step 1: Downloading video...")
        video_file_path = download_video(video_url)
        
        # Step 2: Convert to audio (try local FFmpeg first for speed, then external service as fallback)
        print("[CONVERT] Step 2: Converting to audio...")
        audio_file_path = None
        
        try:
            # Try local FFmpeg conversion first (much faster - no upload needed)
            print("[LOCAL] Trying local FFmpeg conversion...")
            audio_file_path = convert_video_to_audio_local(video_file_path)
        except Exception as local_error:
            print(f"[ERROR] Local FFmpeg failed: {str(local_error)[:100]}...")
            print("[CLOUD] Falling back to external conversion service...")
            
            try:
                # Fallback to external conversion service
                audio_file_path = convert_video_to_audio(video_file_path)
            except Exception as external_error:
                raise Exception(f"Both conversion methods failed. Local: {str(local_error)[:50]}... External: {str(external_error)[:50]}...")
        
        if not audio_file_path:
            raise Exception("No audio file was created")
            
        print(f"[SUCCESS] Audio conversion completed: {os.path.basename(audio_file_path)}")
        
        # Step 3: Clean up video file (optional)
        try:
            if os.path.exists(video_file_path):
                os.remove(video_file_path)
                print("[CLEANUP] Temporary video file cleaned up")
        except:
            pass  # Don't fail if cleanup fails
        
        return audio_file_path
        
    except Exception as e:
        print(f"[ERROR] Error in audio processing: {str(e)}")
        raise e

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("[ERROR] Usage: python audio.py <video_url>")
        sys.exit(1)
    
    video_url = sys.argv[1]
    try:
        result = main(video_url)
        print(f"Audio file ready: {result}")
    except Exception as e:
        print(f"[ERROR] Failed to process: {e}")
        sys.exit(1)
