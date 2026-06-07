#!/usr/bin/env python3
"""Process X bookmark dynamically - scrape, analyze, save, push."""
import json
import sys
import os

# Add RolloForge to path
sys.path.insert(0, '/home/ubuntu/RolloForge')

from datetime import datetime, timezone
from rolloforge.storage import load_bookmarks, save_bookmarks, load_analysis_results
from rolloforge.deepseek_analysis import analyze_with_deepseek
from rolloforge.telegram_ingest import parse_frictionless_url, bookmark_from_parsed_message
from rolloforge.scrapers.x_scraper import fetch_x_content_sync
from rolloforge.utils import stable_bookmark_id, utc_now_iso
from rolloforge.tagging import clean_tags
from rolloforge.bucketing import refine_bucket
from rolloforge.analysis_cleanup import clean_analysis_text
from rolloforge.git_auto import git_auto_push
from rolloforge.similarity import check_duplicate_topic

# URL to process
url = sys.argv[1] if len(sys.argv) > 1 else "https://x.com/systematicls/status/2046215145366704340?s=20"

print(f"🔍 Processing: {url}")

# Step 1: Scrape X content
print("🌐 Scraping X content...")
try:
    scraped = fetch_x_content_sync(url)
    text = scraped.get('text', '')
    author = scraped.get('author', '')
    title = scraped.get('title', '') or f"X post by {author}"
    print(f"✅ Scraped: {title[:80]}...")
except Exception as e:
    print(f"⚠️ Scraping failed: {e}")
    # Fallback: extract handle from URL
    parts = url.split('/')
    handle = parts[3] if len(parts) > 3 else "unknown"
    text = f"X post by @{handle}. View on X for full content."
    author = handle
    title = f"X post by @{handle}"

# Step 2: Create bookmark manually
print("📝 Creating bookmark...")
bookmark_id = stable_bookmark_id(url, text)
timestamp = utc_now_iso()

from rolloforge.models import Bookmark
bookmark = Bookmark(
    id=bookmark_id,
    source="x",
    url=url,
    text=text,
    title=title,
    note="Auto-captured from X via Forger agent",
    author=author,
    created_at=timestamp,
    bookmarked_at=timestamp,
    tags=clean_tags([], title, text, url),
    raw_payload={"ingestion_channel": "forger", "scraped": True}
)

# Step 3: Check for duplicate and MERGE bookmarks
from rolloforge.storage import merge_bookmarks

bookmarks = load_bookmarks()
print(f"Loaded {len(bookmarks)} existing bookmarks")

existing_ids = {b.id if hasattr(b, 'id') else b.get('id') for b in bookmarks}
if bookmark.id in existing_ids:
    print(f"DUPLICATE: Bookmark {bookmark.id} already exists")
    sys.exit(0)

similar = check_duplicate_topic(url, title, bookmark.tags, text, [b.to_dict() if hasattr(b, 'to_dict') else b for b in bookmarks])
if similar.get('similar') and similar['similar'][0].get('score', 0) >= 0.82:
    top = similar['similar'][0]['bookmark']
    print(f"DUPLICATE_TOPIC: {top.get('id')} :: {similar.get('message')}")
    sys.exit(0)

# MERGE — never replace
merged = merge_bookmarks(bookmarks, [bookmark])
save_bookmarks(merged)
print(f"✅ Saved bookmark. Total: {len(merged)} bookmarks")

# SAFETY CHECK
if len(merged) < len(bookmarks):
    raise RuntimeError(f"DATA CORRUPTION: Lost {len(bookmarks) - len(merged)} bookmarks!")

# Step 4: DeepSeek analysis
print("🤖 Running DeepSeek analysis...")
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

# Step 5: Save analysis using MERGE (never overwrite)
from rolloforge.storage import upsert_analysis_results
from rolloforge.models import AnalysisResult, ScoringInputs

print("🤖 Loading existing analyses...")
existing = load_analysis_results()
print(f"Loaded {len(existing)} existing analyses")

scoring = ScoringInputs(**analysis["scoring_inputs"])
new_analysis = AnalysisResult(
    bookmark_id=bookmark.id,
    summary=analysis["summary"],
    recommendation_bucket=analysis["recommendation_bucket"],
    recommendation_reason=analysis["recommendation_reason"],
    key_insights=analysis["key_insights"],
    scoring_inputs=scoring,
    priority_score=analysis["priority_score"],
    worth_score=analysis["worth_score"],
    effort_score=analysis["effort_score"],
    analysis_source=analysis["analysis_source"],
    analyzed_at=analysis["analyzed_at"],
)
new_analysis.recommendation_bucket = refine_bucket(bookmark, new_analysis)
new_analysis = clean_analysis_text(bookmark, new_analysis)
analysis["recommendation_bucket"] = new_analysis.recommendation_bucket
analysis["summary"] = new_analysis.summary
analysis["recommendation_reason"] = new_analysis.recommendation_reason

# MERGE — never replace
merged = upsert_analysis_results(existing, [new_analysis])
print(f"✅ Saved analysis. Total: {len(merged)} analyses")

# SAFETY CHECK
if len(merged) < len(existing):
    raise RuntimeError(f"DATA CORRUPTION: Lost {len(existing) - len(merged)} analyses!")
if len(merged) < 100:
    raise RuntimeError(f"DATA CORRUPTION: Only {len(merged)} analyses left!")

# Step 6: Sync to web dashboard
# Step 6: Sync to web dashboard
print("🔄 Syncing to web dashboard...")
try:
    import subprocess
    result = subprocess.run(
        ["node", "web/lib/copy-data.js"],
        cwd="/home/ubuntu/RolloForge",
        capture_output=True,
        text=True,
        check=True
    )
    print(result.stdout.strip())
    print("✅ Dashboard data synced")
except Exception as e:
    print(f"⚠️ Dashboard sync failed: {e}")
    # Don't fail the whole pipeline for sync issues

# Step 7: Git commit and push
print("📤 Committing and pushing...")
try:
    bucket = analysis['recommendation_bucket']
    priority = analysis['priority_score']
    commit_msg = f"Add: {title[:50]} | {bucket} | {priority}"
    git_auto_push(commit_msg)
    print(f"✅ Pushed to GitHub")
except Exception as e:
    print(f"⚠️ Git push failed: {e}")

# Report
result = {
    "title": title,
    "bucket": analysis['recommendation_bucket'],
    "priority": analysis['priority_score'],
    "tags": clean_tags(deepseek_result.get('tags', []) if deepseek_result else [], title, text, url),
    "bookmark_id": bookmark.id,
    "url": url
}
print("\n" + "="*60)
print(json.dumps(result, indent=2))
print("="*60)
