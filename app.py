from flask import Flask, request, jsonify, send_file
import os
import sys
import tempfile
from audio import main as process_audio
from flask_cors import CORS
import logging

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

app = Flask(__name__)
# Enable CORS to allow requests from Node.js server at port 3000
CORS(app)

# Configure logging to reduce verbosity
logging.getLogger('werkzeug').setLevel(logging.WARNING)
app.logger.setLevel(logging.INFO)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'FreeFBZone Audio Processing Server is running!',
        'endpoints': {
            'POST /download-audio': 'Download audio from Facebook video',
            'GET /health': 'Health check'
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'audio-processing'})

@app.route('/download-audio', methods=['POST'])
def download_audio():
    try:
        data = request.get_json()
        video_url = data.get('videoUrl')
        
        if not video_url:
            return jsonify({'error': 'Video URL is required'}), 400
        
        print(f"Processing audio download for: {video_url}")
        
        # Process the video and get audio file
        audio_file_path = process_audio(video_url)
        
        if not audio_file_path or not os.path.exists(audio_file_path):
            return jsonify({'error': 'Failed to process audio'}), 500
        
        print(f"Audio file ready: {audio_file_path}")
        
        # Send the audio file to user
        return send_file(
            audio_file_path, 
            as_attachment=True, 
            download_name='freefbzone_audio.mp3',
            mimetype='audio/mpeg'
        )
        
    except Exception as e:
        print(f"Error in download_audio: {str(e)[:200]}...")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask Audio Processing Server on port 5000...")
    app.run(debug=True, port=5000, host='127.0.0.1')
