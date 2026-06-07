FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# - chromium: For Playwright browser automation
# - chromium-driver: WebDriver for Chromium
# - curl/wget: Health checks and debugging
# - git: For git operations within the container
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    curl \
    wget \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set Playwright environment variables for Chromium
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/bin/chromium
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium

# Create app directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt requirements-security.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt -r requirements-security.txt

# Install Playwright Python package and browsers
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# Copy the rest of the application
COPY . .

# Create data directory if it doesn't exist
RUN mkdir -p /app/data /app/logs

# Make scripts executable
RUN chmod +x forge scripts/environment-setup/entrypoint.sh

# Expose port for API (if needed in future)
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["./scripts/environment-setup/entrypoint.sh"]
