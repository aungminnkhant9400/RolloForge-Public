# RolloForge

Bookmark intelligence for AI agents. 

Scrapes, analyzes, scores, and organizes bookmarks — deployed as a dark-themed Next.js dashboard on Vercel.

## Features

- **Multi-source scraping** — X/Twitter (via Playwright + jina.ai fallback), articles, GitHub repos
- **AI-powered analysis** — DeepSeek scoring with personalized priority adjustment
- **Dark-mode dashboard** — Next.js static site with bucket-based organization
- **SQLite backend** — Fast local storage with JSON mirroring
- **Automated deployment** — Git push → Vercel deploy

## Quick Start

```bash
cp .env.example .env
# Fill in your API keys in .env
pip install -r requirements.txt
cd web && npm install && npm run dev
```

## Architecture

```
User sends URL → Scrape → Analyze (DeepSeek) → Personalize → SQLite → JSON mirrors → Dashboard
```

## Environment Variables

See `.env.example` for all required variables.

## License

MIT
