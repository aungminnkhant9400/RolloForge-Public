# RolloForge Web Dashboard

A responsive web dashboard for viewing and filtering your RolloForge bookmarks.

## Features

- **Overview Tab**: Stats cards and recent bookmarks
- **Bookmarks Tab**: Full filtering by bucket and tags, plus search
- **Responsive Design**: Works on phone and desktop
- **No Backend**: Reads directly from JSON files

## Local Development

```bash
cd web
npm install
# Copy data files first
npm run data
npm run dev
```

Open http://localhost:3000

## Build for Production

```bash
cd web
npm run data
npm run build
```

Static files output to `web/dist/`

## Data Source

The dashboard reads from parent directory JSON files:
- `../data/bookmarks_raw.json`
- `../data/analysis_results.json`

Run `npm run data` to copy them before building.

## Deployment

### Vercel Dashboard

1. Go to https://vercel.com/new
2. Import your GitHub repo
3. **Important**: Set "Root Directory" to `web`
4. Set **Build Command**: `npm run data && npm run build`
5. Deploy

URL: https://rolloforge.vercel.app

Last updated: 2026-03-22
