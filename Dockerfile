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

# Create a startup script
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'set -e' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# Start Xvfb for headless browser automation' >> /app/start.sh && \
    echo 'Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &' >> /app/start.sh && \
    echo 'sleep 2' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# Verify port from environment' >> /app/start.sh && \
    echo 'echo "Starting server on port: ${PORT:-10000}"' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# Start Node.js server' >> /app/start.sh && \
    echo 'exec node server.js' >> /app/start.sh && \
    chmod +x /app/start.sh

# Expose port
EXPOSE 10000

# Start the application
CMD ["/bin/bash", "/app/start.sh"]
