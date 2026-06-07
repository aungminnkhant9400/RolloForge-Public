# RolloForge Architecture Notes

## Critical Components - DO NOT REMOVE

### X/Twitter Content Fetching (Playwright Scraper)
**Status:** ESSENTIAL - Required for X bookmark analysis

**Why it exists:**
- X blocks direct scraping from bots
- We need tweet content to run AI analysis
- Without content, bookmarks get placeholder text → low priority scores

**How it works:**
- Uses Playwright (headless browser) to load X pages
- Extracts tweet text, author, metadata
- Falls back to API or manual input if scraping fails

**Integration points:**
- `rolloforge/scrapers/x_scraper.py` - Main scraper
- Called from `rolloforge/telegram_ingest.py` when URL-only X links are received
- Saves content to `bookmarks_raw.json` before analysis

**Scaling considerations:**
- Rate limits: Add delays between requests
- Blocking: Rotate user agents, use residential proxies if needed
- Fallbacks: Always have API + manual input as backup

**Last working:** March 2025
**Removed:** Accidentally removed during DeepSeek cleanup
**To restore:** See git history or recreate from this doc

---

## Bookmark Ingestion Workflow

1. **Receive URL** (Telegram)
2. **Detect source** (X, GitHub, article, etc.)
3. **Fetch content** (scraper for X, direct fetch for articles)
4. **Save bookmark** (with full text)
5. **Run AI analysis** (priority scoring, bucket assignment)
6. **Generate report** (bmreport)
7. **Deploy dashboard** (Vercel)

**Dependencies between steps:**
- Step 3 → 4: Must have content before saving
- Step 4 → 5: Analysis needs content to score
- Step 5 → 6: Report needs analysis results

---

## Known Limitations

### X Scraping
- X actively blocks scrapers
- Requires Playwright (headless browser)
- May need rate limiting for high volume
- Fallback: User pastes tweet text

### Article Fetching
- Most sites work fine
- Some block bots (use standard headers)
- JavaScript-rendered sites need Playwright too

---

## Future Scaling

### If adding new sources:
1. Add source detection in `rolloforge/telegram_ingest.py`
2. Create scraper in `rolloforge/scrapers/`
3. Test content extraction
4. Document in this file
5. Add fallback behavior

### If removing dependencies:
1. Check if any scrapers depend on it
2. Check git history for why it was added
3. Document removal reason here
4. Ensure fallback still works
