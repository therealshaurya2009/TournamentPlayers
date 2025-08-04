# Start with slim Python base
FROM python:3.11-slim

# Install system dependencies for Chrome & Selenium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    curl \
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
    libpangocairo-1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libxss1 \
    libxext6 \
    libfontconfig1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Add Chrome signing key & repo
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg \
 && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Install Google Chrome stable
RUN apt-get update && apt-get install -y google-chrome-stable && rm -rf /var/lib/apt/lists/*

# Symlink for compatibility
RUN ln -s /usr/bin/google-chrome-stable /usr/bin/google-chrome

# Install ChromeDriver matching Chrome version
RUN CHROME_VERSION=$(google-chrome --version | grep -oP "\d+\.\d+\.\d+") && \
    CHROMEDRIVER_VERSION=$(curl -sS "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}") && \
    wget -O /tmp/chromedriver_linux64.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" && \
    unzip /tmp/chromedriver_linux64.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver_linux64.zip && \
    chmod +x /usr/local/bin/chromedriver

# Set environment variables
ENV CHROME_BIN=/usr/bin/google-chrome
ENV PATH="$PATH:/usr/local/bin"

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Expose your Flask port
EXPOSE 10000

# Start your app using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
