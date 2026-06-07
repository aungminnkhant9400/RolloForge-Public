# RolloForge Workflow Documentation

**Created:** 2026-03-23
**Purpose:** Document complete workflow for bookmark management

---

## User Profile

**Current Focus:**
- OpenClaw (primary)
- Multi-agent systems
- AI trading strategies
- Polymarket prediction markets

**Stage:** Building by learning

**High Priority:**
- OpenClaw setup & customization
- Multi-agent workflows
- Polymarket/prediction markets
- AI-driven trading strategies
- Stock analysis automation

**Low Priority:**
- Pure theory without code
- Crypto (unless trading-related)
- General AI news

---

## Workflow

### 1. User Pastes URL
```
https://x.com/user/status/123456
```

### 2. I Scrape Content
- **X/Twitter:** Playwright headless browser
- **Articles:** Direct HTTP fetch
- **GitHub:** API fetch

### 3. I Analyze (Garfis Manual Analysis)
**I read the content and write:**
- **Polished title** (clean, no dots, professional)
- **Summary** (what it is, why it matters)
- **Key insights** (3-5 bullet points)
- **Bucket assignment** (test_this_week/build_later/archive/ignore)
- **Priority score** (0-10 based on user profile)
- **Personalized recommendation** (why YOU should care)

**Scoring criteria:**
- Topic match (OpenClaw/trading = high)
- Actionability (code to fork = high)
- Source credibility (Karpathy +1.5)
- Effort vs value

### 4. Save to Database
- `data/bookmarks_raw.json` - bookmark data
- `data/analysis_results.json` - analysis with source: "garfis"

### 5. Commit & Push
```bash
git add data/
git commit -m "Add bookmark: [title]"
git push origin main
```

### 6. Auto-Deploy
- Vercel detects push
- Rebuilds dashboard
- Live in ~30 seconds

### 7. Confirmation
Brief confirmation in chat:
- Title
- Bucket
- Priority
- "Deployed"

---

## Analysis Format

**Title format:**
- Concise, professional
- No trailing dots
- No hashtags
- Example: "Autoresearch Guide: 100 Experiments Overnight"

**Summary format:**
```
What it is: [1-2 sentence description]
Why you should care: [personalized to user's profile]
Key takeaway: [actionable insight]
```

**Bucket criteria:**
- **test_this_week:** Priority ≥6, OpenClaw/trading related, immediate actionable
- **build_later:** Priority ≥4, valuable but not urgent
- **archive:** Reference material, worth keeping
- **ignore:** Low value, not relevant

---

## Handling X Posts

**If text only:** Scrape and analyze

**If has embedded content:**
1. Extract YouTube/article links
2. Fetch content from linked source
3. Analyze full content

**If media-only (image/video):**
1. Check for embedded links
2. If no text available → mark as "limited content"
3. Recommend viewing on X directly

---

## Duplicates

**Check for:**
- Exact URL matches
- Same author + similar content
- Same URL without query params

**Keep:** First occurrence, best analysis

---

## Total Bookmarks

**Current count:** 45
**Analysis source:** garfis (all)
**Dashboard:** https://rolloforge.vercel.app

---

## Commands

**Save bookmark:** (automatic on URL paste)

**Generate report:**
```
bmreport
```

**Full workflow confirmation:**
```
to rolloforge
bookmark this
```

---

## Critical Components

### X Scraper (`rolloforge/scrapers/x_scraper.py`)
- **DO NOT REMOVE**
- Essential for X content extraction
- Multiple fallback selectors
- Blocks images for speed

### Manual Analysis (`scripts/manual_analysis.py`)
- Replaces auto-scoring
- Enables Garfis to write real insights
- Personalized to user profile

---

## Notes

- **No asking for confirmation** on every bookmark
- **No "I can't analyze"** - always try to extract content
- **No placeholder summaries** - always write real analysis
- **No trailing dots** in titles
- **Always check for embedded links** in X posts
- **Always save with source: "garfis"**

---

**Last updated:** 2026-03-23
**Total bookmarks analyzed:** 45