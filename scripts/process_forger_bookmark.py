#!/usr/bin/env python3
"""Process X bookmark with DeepSeek analysis."""
import json
import sys
sys.path.insert(0, '/home/ubuntu/RolloForge')

from datetime import datetime, timezone
from rolloforge.storage import load_bookmarks, save_bookmarks, load_analysis_results, merge_bookmarks, upsert_analysis_results
from rolloforge.deepseek_analysis import analyze_with_deepseek
from rolloforge.telegram_ingest import parse_frictionless_url, bookmark_from_parsed_message, _generate_title
from rolloforge.utils import stable_bookmark_id, utc_now_iso

# URL to process
url = "https://www.facebook.com/share/p/15kcQWK3QWy/"

# Extract handle from URL for fallback text
handle = "Facebook"

# Facebook post - use placeholder text since scraping is limited
text = f"Facebook post. View on Facebook for full content."
author = "Facebook"
title = f"Facebook post"

# Create bookmark manually
bookmark_id = stable_bookmark_id(url, text)
timestamp = utc_now_iso()

bookmark_data = {
    "id": bookmark_id,
    "source": "facebook",
    "url": url,
    "text": text,
    "title": title,
    "note": "Auto-captured from Facebook via Forger agent (scraping limited, URL-only)",
    "author": author,
    "created_at": timestamp,
    "bookmarked_at": timestamp,
    "tags": ["general"],
    "raw_payload": {
        "ingestion_channel": "forger",
        "capture_mode": "url_only",
        "scraped_via": None,
        "scraping_failed": True
    }
}

# Save bookmark
bookmarks = load_bookmarks()

# Check for duplicate
existing_ids = {b.id if hasattr(b, 'id') else b.get('id') for b in bookmarks}
if bookmark_id in existing_ids:
    print(f"DUPLICATE: Bookmark {bookmark_id} already exists")
    sys.exit(0)

# Convert dict to proper format for saving
from rolloforge.models import Bookmark
bookmark = Bookmark(
    id=bookmark_data["id"],
    source=bookmark_data["source"],
    url=bookmark_data["url"],
    text=bookmark_data["text"],
    title=bookmark_data["title"],
    note=bookmark_data["note"],
    author=bookmark_data["author"],
    created_at=bookmark_data["created_at"],
    bookmarked_at=bookmark_data["bookmarked_at"],
    tags=bookmark_data["tags"],
    raw_payload=bookmark_data["raw_payload"]
)

merged_bookmarks = merge_bookmarks(bookmarks, [bookmark])
save_bookmarks(merged_bookmarks)
print(f"✅ Saved bookmark: {bookmark.id}")

# DeepSeek analysis with limited context
deepseek_result = analyze_with_deepseek(
    text=text,
    title=title,
    url=url
)

if deepseek_result:
    analysis = {
        "bookmark_id": bookmark.id,
        "summary": deepseek_result.get('summary', 'Analysis pending'),
        "recommendation_reason": deepseek_result.get('reasoning', ''),
        "key_insights": deepseek_result.get('key_insights', []),
        "scoring_inputs": {
            "relevance": deepseek_result.get('relevance', 5.0),
            "practical_value": deepseek_result.get('practical_value', 5.0),
            "actionability": deepseek_result.get('actionability', 5.0),
            "stage_fit": 5.0,
            "novelty": 5.0,
            "excitement": 5.0,
            "difficulty": 5.0,
            "time_cost": 3.0,
        },
        "worth_score": deepseek_result.get('worth_score', deepseek_result.get('priority_score', 5.0)),
        "effort_score": deepseek_result.get('effort_score', 3.0),
        "priority_score": deepseek_result.get('priority_score', 5.0),
        "recommendation_bucket": deepseek_result.get('recommendation_bucket', deepseek_result.get('bucket', 'archive')),
        "analysis_source": deepseek_result.get('analysis_source', 'deepseek'),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
    print(f"✅ Analysis complete - Bucket: {analysis['recommendation_bucket']}")
else:
    analysis = {
        "bookmark_id": bookmark.id,
        "summary": "DeepSeek analysis failed",
        "recommendation_reason": "AI analysis failed",
        "key_insights": [],
        "scoring_inputs": {"relevance": 0, "practical_value": 0, "actionability": 0, "stage_fit": 0, "novelty": 0, "excitement": 0, "difficulty": 0, "time_cost": 0},
        "worth_score": 0.0,
        "effort_score": 0.0,
        "priority_score": 0.0,
        "recommendation_bucket": "pending",
        "analysis_source": "failed",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
    print("❌ Analysis failed")

# Save analysis safely
from rolloforge.models import AnalysisResult, ScoringInputs
existing = load_analysis_results()
new_analysis = AnalysisResult(
    bookmark_id=bookmark.id,
    summary=analysis['summary'],
    recommendation_reason=analysis['recommendation_reason'],
    key_insights=analysis['key_insights'],
    scoring_inputs=ScoringInputs(**analysis['scoring_inputs']),
    worth_score=analysis['worth_score'],
    effort_score=analysis['effort_score'],
    priority_score=analysis['priority_score'],
    recommendation_bucket=analysis['recommendation_bucket'],
    analysis_source=analysis['analysis_source'],
    analyzed_at=analysis['analyzed_at'],
)
merged = upsert_analysis_results(existing, [new_analysis])
print(f"✅ Saved analysis. Total: {len(merged)}")
print(json.dumps({"bookmark_id": bookmark.id, "bucket": analysis['recommendation_bucket'], "priority": analysis['priority_score']}, indent=2))
