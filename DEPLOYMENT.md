# RolloForge Deployment

## Dashboard Architecture

Static Next.js site deployed to Vercel. Data is baked in at build time.

## Data Flow

1. Bookmarks saved → `data/bookmarks_raw.json`
2. Analysis saved → `data/analysis_results.json`
3. Git commit → Vercel auto-deploy
4. Build script `npm run data` copies files to `web/lib/`
5. Next.js static export generates HTML

## Vercel Configuration

- **Root Directory:** `web` (set in vercel.json)
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Framework:** Next.js with static export

## Build Issues History

**2026-04-18:** Fixed rootDirectory misconfiguration causing builds to fail immediately (0ms).
