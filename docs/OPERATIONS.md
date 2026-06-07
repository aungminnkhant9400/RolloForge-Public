# OPERATIONS.md - RolloForge Day-to-Day Operations

## Quick Reference

### Adding a Bookmark

**Via CLI (recommended):**
```bash
cd /home/ubuntu/RolloForge
forge add "https://x.com/user/status/123456"
```

**Via Python:**
```bash
python scripts/save_bookmark.py "https://example.com/article"
```

**Via Telegram:**
Forward any URL to the RolloForge bot.

---

### Running the Scraper Pipeline

**Full pipeline (scrape + analyze + sync):**
```bash
forge pipeline
```

**Manual analysis only:**
```bash
python scripts/analyze_bookmarks.py
```

**Sync X bookmarks specifically:**
```bash
python scripts/sync_x_bookmarks.py
```

---

### Checking Dashboard Status

**Quick stats:**
```bash
forge stats
```

**Health check:**
```bash
forge health
```

**View dashboard:**
https://rollo-forge.vercel.app

---

### Weekly Digest

**Generate and send via Telegram:**
```bash
forge digest --send-telegram
```

**Generate only:**
```bash
forge digest --save
```

---

## Common Issues & Fixes

### DeepSeek Analysis Fails
**Symptom:** Bookmarks saved but no analysis generated
**Fix:**
```bash
# Check API key
head -1 .env
# If invalid, update with new key from DeepSeek dashboard
```

### Duplicates Appearing
**Symptom:** Same URL saved multiple times
**Fix:** The system now normalizes URLs before checking. Run health check:
```bash
forge health
```

### Dashboard Not Updating
**Symptom:** New bookmarks not showing on site
**Fix:**
```bash
cd web && npm run data
# Or full rebuild:
cd web && npm run build
```

### Git Push Fails
**Symptom:** Cannot push to GitHub
**Fix:**
```bash
# Check status
git status
# If conflicts in JSON files:
git checkout --theirs data/bookmarks_raw.json data/analysis_results.json
git add data/
git commit -m "Resolve data conflicts"
```

### X Scraper Issues
**Symptom:** X bookmarks not scraping
**Fix:**
- Check if logged in: `python scripts/get_x_user_token.py`
- If rate limited, wait 15 minutes
- Alternative: Save URL manually with note "X post"

---

## Directory Structure

```
/home/ubuntu/RolloForge/
├── data/               # Raw data (bookmarks, analyses)
├── web/                # Next.js dashboard
├── scripts/            # Utility scripts
├── reports/            # Generated reports
└── docs/               # Documentation
```

## Environment Variables

Required in `.env`:
```
DEEPSEEK_API_KEY=sk-...
```

Optional:
```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```
