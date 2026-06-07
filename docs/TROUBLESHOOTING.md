# TROUBLESHOOTING.md - Common Problems & Solutions

## Scraper Failures

### X/Twitter Rate Limit
**Symptoms:**
- "Rate limited" errors
- Empty text in X bookmarks
- Scraper timeouts

**Diagnosis:**
```bash
python scripts/sync_x_bookmarks.py --dry-run
```

**Fixes:**
1. Wait 15-30 minutes
2. Check if logged in: `python scripts/get_x_user_token.py`
3. Use manual bookmarking as fallback

**Prevention:**
- Space out X scraping (don't bulk import)
- Use `--delay` flag if available

---

## DeepSeek API Issues

### Rate Limit (429)
**Symptoms:**
- "Too many requests" errors
- Analysis queue backing up

**Diagnosis:**
```bash
tail -50 logs/analysis.log | grep -i error
```

**Fixes:**
1. Implement exponential backoff
2. Batch requests (current: 10/min)
3. Check DeepSeek dashboard for limits

### API Key Invalid
**Symptoms:**
- "Authentication failed"
- No analysis generated

**Fixes:**
```bash
# Check current key
head -1 .env
# Generate new key at platform.deepseek.com
# Update .env (NEVER commit this file)
```

### Parsing Errors
**Symptoms:**
- Analysis has garbled text
- Missing fields in output

**Fixes:**
1. Check DeepSeek API status
2. Verify JSON is valid: `python -m json.tool data/analysis_results.json`
3. Re-run analysis: `python scripts/analyze_bookmarks.py --retry-failed`

---

## Dashboard Build Failures

### Vercel Build Error
**Symptoms:**
- Red X on Vercel dashboard
- "Build failed" notification

**Diagnosis:**
```bash
cd web
npm run build 2>&1 | tee build.log
```

**Common Fixes:**
| Error | Fix |
|-------|-----|
| TypeScript errors | Run `npx tsc --noEmit` locally |
| Missing data files | Run `npm run data` first |
| Out of memory | Reduce parallel builds in Vercel settings |

### Blank Page
**Symptoms:**
- Site loads but content is empty
- Console shows JSON errors

**Fixes:**
```bash
# Re-sync data
cp data/bookmarks_raw.json web/lib/data.json
cp data/analysis_results.json web/lib/analysis.json
# Verify JSON validity
python -m json.tool web/lib/data.json > /dev/null && echo "Valid"
```

---

## Data Sync Problems

### Missing Bookmarks
**Symptoms:**
- Bookmarks in `data/` but not on dashboard
- Partial data display

**Diagnosis:**
```bash
# Check counts
jq length data/bookmarks_raw.json
jq length web/lib/data.json
```

**Fixes:**
```bash
# Force re-sync
cd web && npm run data
# Or manual copy
cp data/bookmarks_raw.json web/lib/data.json
cp data/analysis_results.json web/lib/analysis.json
```

### Duplicate Bookmarks
**Symptoms:**
- Same URL appears multiple times
- Similar titles different IDs

**Fixes:**
```bash
# Run health check
python scripts/bookmark_health_dashboard.py
# Check for similar bookmarks
python -c "
import json
with open('data/bookmarks_raw.json') as f:
    b = json.load(f)
urls = [x['url'] for x in b]
dups = [u for u in urls if urls.count(u) > 1]
print('Duplicates:', set(dups))
"
```

---

## Git/Merge Conflicts

### Push Rejected
**Symptoms:**
- "Updates were rejected"
- "Non-fast-forward"

**Fixes:**
```bash
# Pull first
git pull origin main
# If conflicts in data files:
git checkout --theirs data/bookmarks_raw.json
git checkout --theirs data/analysis_results.json
git add data/
git commit -m "Resolve data conflicts"
git push
```

### JSON Merge Conflicts
**Symptoms:**
- `<<<<<<< HEAD` in JSON files
- Parser errors

**Fixes:**
1. Keep server's version (usually newer data)
2. Or manually merge if you know which is correct
3. Validate after: `python -m json.tool file.json`

**Prevention:**
- Pull before pushing
- Don't edit data files manually on multiple machines
- Use the automation scripts instead

---

## Performance Issues

### Slow Dashboard Load
**Symptoms:**
- Page takes >5 seconds to load
- Browser freezes

**Diagnosis:**
```bash
# Check data file size
ls -lh web/lib/*.json
# If >10MB, consider pagination
```

**Fixes:**
- Archive old bookmarks (move to `archive` bucket)
- Implement client-side pagination
- Lazy load bookmark details

### High Memory Usage
**Symptoms:**
- Analysis script OOM killed
- System slowdown during pipeline

**Fixes:**
```bash
# Process in smaller batches
python scripts/analyze_bookmarks.py --batch-size 10
# Or use parallel workers with rate limiting
```

---

## Recovery Procedures

### Complete Data Loss
**If data files are corrupted:**
```bash
# Restore from git
git checkout HEAD -- data/bookmarks_raw.json
git checkout HEAD -- data/analysis_results.json
# Re-analyze if needed
python scripts/analyze_bookmarks.py
```

### Reset Everything
**Nuclear option (keeps git history):**
```bash
cd /home/ubuntu/RolloForge
rm -rf data/*.json
python scripts/run_pipeline.py --full-reset
```

---

## Getting Help

1. Check logs: `logs/*.log`
2. Run health check: `forge health`
3. Check git status: `git status`
4. Verify JSON: `python -m json.tool data/file.json`
