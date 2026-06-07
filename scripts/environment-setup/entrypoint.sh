#!/bin/bash
set -e

echo "=========================================="
echo "  RolloForge Container Entrypoint"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Ensure data directory exists
mkdir -p /app/data /app/logs

# Check if .env exists, create from example if not
if [ ! -f "/app/.env" ] && [ -f "/app/.env.example" ]; then
    print_warning ".env not found, copying from .env.example"
    cp /app/.env.example /app/.env
fi

# Verify DeepSeek API key is set
if [ -z "$DEEPSEEK_API_KEY" ]; then
    print_warning "DEEPSEEK_API_KEY not set. Some features will not work."
fi

# Test Python imports
echo ""
echo "Verifying Python environment..."
python -c "
import sys
sys.path.insert(0, '/app')

# Test core imports
try:
    from rolloforge.deepseek_analysis import get_deepseek_client
    print('  ✓ DeepSeek module loaded')
except ImportError as e:
    print(f'  ✗ DeepSeek module failed: {e}')

try:
    from rolloforge.scrapers.x_scraper import scrape_x_post
    print('  ✓ X Scraper module loaded')
except ImportError as e:
    print(f'  ✗ X Scraper module failed: {e}')

try:
    import playwright
    print('  ✓ Playwright loaded')
except ImportError as e:
    print(f'  ✗ Playwright failed: {e}')

try:
    import requests
    print('  ✓ Requests loaded')
except ImportError as e:
    print(f'  ✗ Requests failed: {e}')
"

# Test Playwright browser installation
echo ""
echo "Verifying Playwright browsers..."
python -c "
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        browser.close()
        print('  ✓ Chromium browser working')
except Exception as e:
    print(f'  ✗ Chromium browser failed: {e}')
"

echo ""
print_status "Environment verification complete"
echo ""

# Keep container running with a simple HTTP server for health checks
# This allows the container to stay up and be exec'd into for CLI commands
echo "Starting health check server on port 8000..."
echo "Container is ready. Use 'docker-compose exec rolloforge-api bash' to access CLI."
echo ""

# Simple Python HTTP server for health checks
python -c "
import http.server
import socketserver
import json
import os

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = {'status': 'healthy', 'service': 'rolloforge-api'}
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'RolloForge API is running. Use /health for status.')
    
    def log_message(self, format, *args):
        # Suppress request logs
        pass

with socketserver.TCPServer(('', 8000), HealthHandler) as httpd:
    print('Health server running at http://localhost:8000')
    httpd.serve_forever()
"
