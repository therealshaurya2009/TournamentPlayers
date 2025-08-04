# Use Selenium standalone Chrome image with Chrome & ChromeDriver preinstalled
FROM selenium/standalone-chrome:latest

# Switch to root to install python and dependencies
USER root

# Update and install python3 and pip
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Copy Python dependencies file and install
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the entire app source code
COPY . /app/

# Expose the port your Flask app listens on
EXPOSE 10000

# Run your Flask app with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
