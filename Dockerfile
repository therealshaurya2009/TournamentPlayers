FROM python:3.11-slim

# Install dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg ca-certificates \
    libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 \
    libx11-dev libxcomposite1 libxdamage1 libxrandr2 \
    libasound2 libatk1.0-0 libgtk-3-0 libxss1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its browser binaries
RUN playwright install --with-deps

# Expose port for Flask app
EXPOSE 10000

# Start Flask app (replace with your file if different)
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
