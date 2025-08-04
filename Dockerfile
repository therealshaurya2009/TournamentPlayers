# Use official slim Python image
FROM python:3.11-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    unzip \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxrandr2 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libxss1 \
    libxext6 \
    libfontconfig1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    ln -s /usr/bin/google-chrome-stable /usr/bin/google-chrome && \
    google-chrome --version

# Install ChromeDriver to match Chrome version
RUN CHROME_VERSION=$(google-chrome --version | grep -oP "\d+\.\d+\.\d+") && \
    CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}") && \
    wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver.zip && \
    chromedriver --version

# Set environment variables
ENV CHROME_BIN=/usr/bin/google-chrome
ENV PATH="${PATH}:/usr/local/bin"

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose your Flask port
EXPOSE 10000

# Start your app
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
