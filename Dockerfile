# Use a lightweight Python image
FROM python:3.11-slim

# Install dependencies for Chrome and ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    gnupg2 \
    curl \
    fonts-liberation \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libxss1 \
    libxext6 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Add Google Chrome repo and install Chrome stable
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget -N https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip -P /tmp && \
    unzip /tmp/chromedriver_linux64.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver_linux64.zip

# Set display port (needed for Chrome)
ENV DISPLAY=:99

# Set workdir
WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . /app/

# Expose port your Flask app listens on (change if needed)
EXPOSE 10000

RUN which google-chrome || echo "google-chrome not found"
RUN which google-chrome-stable || echo "google-chrome-stable not found"
RUN ls -l /opt/google/chrome || echo "/opt/google/chrome not found"
RUN google-chrome --version || echo "google-chrome version check failed"
RUN google-chrome-stable --version || echo "google-chrome-stable version check failed"

# Start the app with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
