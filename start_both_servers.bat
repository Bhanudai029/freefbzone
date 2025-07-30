@echo off
echo Starting FreeFBZone - Dual Server Setup
echo =====================================
echo.
echo Starting Node.js Server (Port 3000) - Video Info & Main Site
start "Node.js Server" cmd /k "echo Node.js Server (Port 3000) & echo. & node server.js"

echo.
echo Waiting 3 seconds before starting Flask server...
timeout /t 3 /nobreak > nul

echo.
echo Starting Flask Server (Port 5000) - Audio Processing  
start "Flask Server" cmd /k "echo Flask Audio Server (Port 5000) & echo. & python app.py"

echo.
echo =====================================
echo Both servers are starting...
echo.
echo Main Website: http://localhost:3000
echo Audio Processing: http://localhost:5000
echo.
echo - Node.js handles video info fetching
echo - Flask handles MP3 audio conversion
echo.
echo Close this window to stop monitoring.
echo Individual server windows can be closed separately.
echo =====================================
pause
