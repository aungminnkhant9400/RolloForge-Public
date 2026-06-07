# DEPLOYMENT.md - RolloForge Deployment Guide

## ⚠️ CRITICAL: Git Push → Auto-Deploy

**NEVER manually deploy to Vercel.**

The correct flow:
```
Git push → GitHub → Vercel (auto-deploy)
```

Manual deploy creates duplicate projects and wastes build minutes.

---

## Initial Setup

### 1. Fork/Clone Repository
```bash
git clone https://github.com/aungminnkhant9400/RolloForge.git
cd RolloForge
```

### 2. Connect to Vercel
1. Go to https://vercel.com/new
2. Import GitHub repository
3. Use these settings:
   - **Framework Preset:** Next.js
   - **Root Directory:** `web`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`

### 3. Configure Environment Variables

In Vercel dashboard → Settings → Environment Variables:

```
# Not needed for static export, but good practice:
NEXT_PUBLIC_APP_URL=https://rollo-forge.vercel.app
```

Local `.env` (not deployed):
```
DEEPSEEK_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

---

## Deployment Verification

### Check Vercel Dashboard
1. Go to https://vercel.com/dashboard
2. Select RolloForge project
3. Check "Deployments" tab
4. Latest push should show "Ready"

### Verify Build Logs
```
Build: Success
Output: dist/
Files: 50+
```

### Check Live Site
1. Visit https://rollo-forge.vercel.app
2. Verify bookmarks load
3. Check bucket filters work
4. Test search functionality

---

## Troubleshooting

### Build Fails
**Symptom:** Red X on Vercel dashboard
**Fix:**
```bash
# Local test
cd web
npm run build
# Fix any TypeScript errors
```

### Old Data Showing
**Symptom:** Dashboard shows stale bookmarks
**Fix:**
```bash
# Re-sync data
cd /home/ubuntu/RolloForge
python scripts/run_pipeline.py
# Or manually:
cp data/bookmarks_raw.json web/lib/data.json
cp data/analysis_results.json web/lib/analysis.json
cd web && npm run build
```

### 404 Errors
**Symptom:** Pages not found
**Fix:** Check `web/next.config.js` has:
```javascript
output: 'export',
distDir: 'dist',
```

---

## Rollback

### Via Vercel Dashboard
1. Go to Deployments tab
2. Find previous working deployment
3. Click "..." → "Promote to Production"

### Via Git
```bash
# Revert to last known good commit
git log --oneline -5
git revert <bad-commit-hash>
git push
```

---

## Environment-Specific Notes

### Local Development
```bash
cd web
npm install
npm run dev
# http://localhost:3000
```

### Production
- Static export (no server-side rendering)
- Data baked at build time
- Updates require new build + deploy

---

## Checklist Before Major Changes

- [ ] Test locally with `npm run build`
- [ ] Check for TypeScript errors
- [ ] Verify data files are valid JSON
- [ ] Commit with clear message
- [ ] Push and wait for Vercel "Ready"
- [ ] Verify live site works
