# Use slim Python base
FROM python:3.11-slim

# Install system packages and Chrome dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip curl gnupg ca-certificates \
    fonts-liberation libnss3 libx11-xcb1 libxcomposite1 libxcursor1 \
    libxdamage1 libxrandr2 libasound2 libatk-bridge2.0-0 libgtk-3-0 \
    libxss1 libxext6 libfontconfig1 xdg-utils && \
    rm -rf /var/lib/apt/lists/*

# Add Chrome signing key and repo
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list

# Install Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable && \
    ln -s /usr/bin/google-chrome-stable /usr/bin/google-chrome

# Install ChromeDriver to match Chrome version
RUN CHROME_VERSION=$(google-chrome --version | grep -oP "\d+\.\d+\.\d+") && \
    DRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}") && \
    wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${DRIVER_VERSION}/chromedriver_linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver.zip

# Diagnostic log (optional)
RUN google-chrome --version && chromedriver --version

# Set environment vars
ENV CHROME_BIN=/usr/bin/google-chrome
ENV PATH="/usr/local/bin:$PATH"

# Set up the app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Expose your app port
EXPOSE 10000

# Start server
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
