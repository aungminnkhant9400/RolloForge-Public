# ARCHITECTURE.md - RolloForge Technical Overview

## Data Flow

```
URL → Scraper → DeepSeek Analysis → JSON Storage → Dashboard
```

1. **Input:** URL from Telegram, CLI, or manual entry
2. **Scraper:** Playwright (X/Twitter) or newspaper3k (articles)
3. **Analysis:** DeepSeek API generates insights, tags, priority
4. **Storage:** JSON files in `data/`
5. **Sync:** Copied to `web/lib/` for dashboard
6. **Deploy:** Git push → Vercel auto-deploy

---

## File Structure

### Core Data Files

| File | Purpose |
|------|---------|
| `data/bookmarks_raw.json` | All saved bookmarks |
| `data/analysis_results.json` | DeepSeek analysis output |
| `data/seen_bookmarks.json` | Deduplication cache |

### Web Dashboard

| Path | Purpose |
|------|---------|
| `web/app/page.tsx` | Main dashboard page |
| `web/components/BookmarkList.tsx` | Bookmark display |
| `web/lib/data.json` | Synced bookmarks (build-time) |
| `web/lib/analysis.json` | Synced analysis (build-time) |

### Scripts

| Script | Purpose |
|--------|---------|
| `save_bookmark.py` | Add single bookmark |
| `analyze_bookmarks.py` | Run DeepSeek analysis |
| `sync_x_bookmarks.py` | Sync from X/Twitter |
| `run_pipeline.py` | Full automation |
| `scripts/weekly_digest.py` | Weekly digest generator |
| `bookmark_health_dashboard.py` | Data integrity checks |

---

## Dependencies

### Python
- `openai` (DeepSeek API client)
- `playwright` (X/Twitter scraping)
- `newspaper3k` (article extraction)
- `python-dotenv` (env vars)

### Node.js
- `next` (dashboard framework)
- `lucide-react` (icons)
- `tailwindcss` (styling)

---

## DeepSeek Analysis Pipeline

### Prompt Template
```python
SYSTEM_PROMPT = """You are an expert content analyzer..."""

USER_PROMPT = f"""Title: {title}
Content: {content[:8000]}
URL: {url}"""
```

### Output Format
```json
{
  "title": "Summarized title",
  "summary": "Brief summary",
  "key_insights": ["point 1", "point 2"],
  "action_items": ["action 1"],
  "tags": ["tag1", "tag2"],
  "priority_score": 7.5,
  "recommendation_bucket": "test_this_week"
}
```

### Buckets
- `test_this_week` - High priority, do soon
- `build_later` - Medium priority, queue for later
- `archive` - Reference material
- `ignore` - Low value

### Scoring Formula
```python
priority = base_score * urgency_multiplier * relevance_multiplier
```

---

## Data Models

### Bookmark
```typescript
interface Bookmark {
  id: string;           // Stable hash
  source: "x" | "article";
  url: string;
  text: string;
  title: string;
  author?: string;
  created_at: string;   // ISO timestamp
  bookmarked_at: string;
  tags: string[];
  note?: string;
  raw_payload: {
    ingestion_channel: string;
    capture_mode: string;
    scraped_via?: string;
  };
}
```

### AnalysisResult
```typescript
interface AnalysisResult {
  bookmark_id: string;
  title: string;
  summary: string;
  key_insights: string[];
  action_items: string[];
  tags: string[];
  priority_score: number;
  recommendation_bucket: string;
  analyzed_at: string;
}
```

---

## Git Workflow

1. **Development:** Work on feature branches
2. **Data updates:** Committed automatically by scripts
3. **Deploy:** Push to main → Vercel auto-deploys

**Never manually deploy to Vercel** — always push to GitHub.

---

## Scraper Architecture

### X/Twitter Scraper
- Uses Playwright to load X.com
- Extracts text, author, timestamp
- Falls back to URL-only if blocked
- Rate limit handling with exponential backoff

### Article Scraper
- Uses newspaper3k for general sites
- Extracts title, text, author, publish date
- Fallback to raw HTML if extraction fails

---

## Dashboard Rendering

- **Build-time:** Data synced from `data/` to `web/lib/`
- **ISR:** Incremental Static Regeneration disabled (static export)
- **Navigation:** Client-side routing between buckets
- **Search:** Client-side filter on title/summary/tags
