# Use prebuilt Alpine image with headless Chromium + Node
FROM zenika/alpine-chrome:with-node

# Set working directory inside container
WORKDIR /app

# Install Python3 and pip (Alpine package manager is apk)
RUN apk add --no-cache python3 py3-pip

# Copy Python dependencies list
COPY requirements.txt /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy all app source code into container
COPY . /app/

# Expose Flask app port (adjust if needed)
EXPOSE 10000

# Add a startup script that prints Chromium version for debugging
RUN echo '#!/bin/sh\nchromium-browser --version\nexec "$@"' > /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# Use startup script to print Chromium version before launching app
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Run Gunicorn server binding to port 10000 and your Flask app
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
