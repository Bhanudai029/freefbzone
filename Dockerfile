# Use a lighter Node.js base image
FROM node:18-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/app
ENV DISPLAY=:99
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome
ENV RENDER=true
ENV PATH="/opt/venv/bin:$PATH"

# Install system dependencies (minimal set)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libnss3 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (lighter installation)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY requirements.txt ./

# Install Node.js dependencies
RUN npm install

# Install Python dependencies in virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create a startup script that runs both servers
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting FreeFBZone services..."\n\
\n\
# Start Xvfb for headless display\n\
echo "Starting Xvfb..."\n\
Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &\n\
XVFB_PID=$!\n\
\n\
# Start Python Flask server in background\n\
echo "Starting Flask server on port 5000..."\n\
export PATH="/opt/venv/bin:$PATH"\n\
python app.py &\n\
FLASK_PID=$!\n\
\n\
# Wait for Flask to start and verify it is running\n\
echo "Waiting for Flask server to start..."\n\
sleep 5\n\
\n\
# Test if Flask server is responding\n\
for i in {1..10}; do\n\
  if curl -f http://localhost:5000/health > /dev/null 2>&1; then\n\
    echo "Flask server is ready!"\n\
    break\n\
  else\n\
    echo "Waiting for Flask server... ($i/10)"\n\
    sleep 2\n\
  fi\n\
  if [ $i -eq 10 ]; then\n\
    echo "Flask server failed to start!"\n\
    exit 1\n\
  fi\n\
done\n\
\n\
# Start Node.js server\n\
echo "Starting Node.js server on port $PORT..."\n\
node server.js' > /app/start.sh && chmod +x /app/start.sh

# Expose ports
EXPOSE 3000 5000

# Start the application
CMD ["/app/start.sh"]
