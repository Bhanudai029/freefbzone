# FreeFBZone Audio Processing Server

A Flask-based server that extracts audio from Facebook videos using SnapSave and converts them to MP3 format.

## 🚀 Features

- **Video Download**: Downloads Facebook videos using SnapSave.app with Playwright automation
- **Audio Conversion**: Converts videos to MP3 using external service or local FFmpeg
- **Dual Conversion Methods**: External cloud service as primary, FFmpeg as fallback
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **API Endpoints**: RESTful API for integration with web applications

## 📋 Requirements

### Python Dependencies
```bash
pip install flask flask-cors requests playwright asyncio
```

### External Dependencies
- **Playwright Browser**: `playwright install chromium`
- **FFmpeg** (optional, for local conversion): Download from https://ffmpeg.org/

## 🔧 Installation

1. **Clone or download the project files**
2. **Install Python dependencies**:
   ```bash
   pip install flask flask-cors requests playwright
   ```
3. **Install Playwright browser**:
   ```bash
   playwright install chromium
   ```
4. **Install FFmpeg** (optional but recommended):
   - Download from https://ffmpeg.org/
   - Add to your system PATH

## 🚀 Usage

### Starting the Server
```bash
python app.py
```
The server will start on `http://127.0.0.1:5000`

### API Endpoints

#### 1. Health Check
```http
GET /health
```
Returns server status

#### 2. Home Page
```http
GET /
```
Returns API information

#### 3. Download Audio
```http
POST /download-audio
Content-Type: application/json

{
    "videoUrl": "https://www.facebook.com/share/v/VIDEO_ID/"
}
```
Returns MP3 file as download

### Testing

Run the test script to verify functionality:
```bash
python test_audio.py
```

## 🏗️ Architecture

### Components

1. **Flask App** (`app.py`): Main web server with API endpoints
2. **Audio Processor** (`audio.py`): Core logic for video download and conversion
3. **SnapSave Downloader** (`snapsave_downloader.py`): Playwright automation for video extraction
4. **Test Suite** (`test_audio.py`): Comprehensive testing tool

### Process Flow

1. **Video Download**: Uses Playwright to automate SnapSave.app for Facebook video extraction
2. **Audio Conversion**: 
   - Primary: External cloud service (videotomp3.onrender.com)
   - Fallback: Local FFmpeg conversion
3. **File Delivery**: Returns MP3 file to client with automatic cleanup

## 🔧 Recent Fixes

### Encoding Issues Fixed
- ✅ Fixed Windows console encoding conflicts
- ✅ Improved stdout/stderr handling
- ✅ Reduced logging verbosity

### Error Handling Improvements
- ✅ Better exception handling throughout the pipeline
- ✅ Graceful fallback from cloud to local conversion
- ✅ Comprehensive error messages and logging

### Code Quality
- ✅ Fixed FFmpeg command syntax error
- ✅ Added proper async/await handling
- ✅ Improved file cleanup and resource management

## 🐛 Troubleshooting

### Common Issues

#### 1. "raw stream has been detached" Error
This is a logging issue that doesn't affect functionality. Fixed in the latest version.

#### 2. FFmpeg Not Found
Install FFmpeg and add to PATH, or rely on the external conversion service.

#### 3. Playwright Browser Issues
Run `playwright install chromium` to ensure browser is properly installed.

#### 4. Connection Timeouts
Large videos may take longer to process. The system has built-in retry mechanisms.

### Debug Mode
The Flask app runs in debug mode by default for development. For production, set `debug=False`.

## 📁 File Structure

```
freefbzone/
├── app.py                    # Flask web server
├── audio.py                  # Audio processing logic
├── snapsave_downloader.py    # Video download automation
├── test_audio.py            # Test suite
├── README.md                # This file
└── requirements.txt         # Python dependencies (create if needed)
```

## 🔒 Security Notes

- The server runs on localhost by default for security
- Temporary files are automatically cleaned up
- No sensitive data is stored persistently

## 📈 Performance

- **Video Download**: ~30-60 seconds depending on video size
- **Audio Conversion**: ~15-30 seconds for cloud service
- **Total Process Time**: Usually under 2 minutes for typical videos

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve the system.

## 📄 License

This project is for educational and personal use. Respect Facebook's terms of service when using this tool.
