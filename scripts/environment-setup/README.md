# RolloForge Development Environment Setup

This directory contains Docker and setup scripts for a reproducible RolloForge development environment.

## Quick Start

### Option 1: Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/aungminnkhant9400/RolloForge.git
cd RolloForge

# Copy environment template
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 2: Local Setup with setup.sh

```bash
# Run the setup script
./scripts/environment-setup/setup.sh

# Activate the virtual environment
source .venv/bin/activate

# Install Playwright browsers
playwright install chromium

# Copy and configure environment
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY
```

## What's Included

### Docker Services

| Service | Description | Port |
|---------|-------------|------|
| `rolloforge-api` | Python backend with all dependencies | 8000 |
| `dashboard` | Next.js development server | 3000 |

### Volumes

- `./data:/app/data` - Bookmark data persistence
- `./web:/app/web` - Dashboard code (hot reload)
- `node_modules` - Node dependencies (named volume)

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
DEEPSEEK_API_KEY=your_key_here

# Optional (for X/Twitter integration)
X_USER_ACCESS_TOKEN=your_token
X_CLIENT_ID=your_client_id
X_CLIENT_SECRET=your_client_secret
```

## Development Workflow

### Python Development

```bash
# Enter the API container
docker-compose exec rolloforge-api bash

# Run CLI commands
python forge.py stats
python forge.py add https://x.com/...

# Run tests
pytest tests/
```

### Dashboard Development

```bash
# The dashboard auto-reloads on code changes
# Access at http://localhost:3000

# To add new dependencies
docker-compose exec dashboard npm install <package>
```

## Troubleshooting

### Playwright Issues

If Playwright browsers fail to install:

```bash
# Inside the container
docker-compose exec rolloforge-api bash
playwright install-deps chromium
playwright install chromium
```

### Permission Issues

If you encounter permission errors with the data directory:

```bash
# Fix permissions
sudo chown -R $USER:$USER data/
chmod -R 755 data/
```

### Port Conflicts

If ports 3000 or 8000 are already in use:

```bash
# Edit docker-compose.yml and change the port mappings:
# ports:
#   - "3001:3000"  # Dashboard on port 3001
#   - "8001:8000"  # API on port 8001
```

## Production Deployment

For production deployment to Vercel:

```bash
# Dashboard only - no Docker needed
cd web
npm run build
vercel --prod
```

The Python backend is designed to run locally or on a VPS for scraping operations.

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `setup.sh` | Local environment setup |
| `docker-compose.yml` | Full stack orchestration |
| `Dockerfile` | Python backend container |
| `entrypoint.sh` | Container startup commands |

## Support

- [RolloForge README](../../README.md)
- [Architecture Notes](../../ARCHITECTURE.md)
- [Security Guide](../../SECURITY.md)
