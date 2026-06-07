#!/usr/bin/env python3
"""Process X bookmark with DeepSeek analysis - dynamic URL version."""
import json
import sys
import hashlib
sys.path.insert(0, '/home/ubuntu/RolloForge')

from datetime import datetime, timezone
from rolloforge.storage import load_bookmarks, save_bookmarks, load_analysis_results
from rolloforge.deepseek_analysis import analyze_with_deepseek
from rolloforge.utils import stable_bookmark_id, utc_now_iso
from rolloforge.scrapers import fetch_x_content_sync

def process_x_url(url):
    """Process an X/Twitter URL through the full Forger pipeline."""
    
    # Step 1: Try to scrape content
    print(f"🔍 Scraping: {url}")
    scraped = fetch_x_content_sync(url)
    
    if scraped and scraped.get('text'):
        text = scraped['text']
        author = scraped.get('author', 'Unknown')
        title = scraped.get('title', text[:100] + '...')
        scraping_failed = False
        capture_mode = "full"
    else:
        # Fallback: extract handle from URL
        handle = url.split('/')[3] if len(url.split('/')) > 3 else 'Unknown'
        
        # Try web_fetch as a last resort
        try:
            import subprocess
            result = subprocess.run(
                ['curl', '-s', '-L', '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', url],
                capture_output=True, text=True, timeout=15
            )
            html = result.stdout
            # Try to extract title from meta tags
            import re
            title_match = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html)
            if title_match:
                title = title_match.group(1)
                text = title
                scraping_failed = False
                capture_mode = "partial"
            else:
                # Clean fallback - just the handle, no "X post from" prefix
                text = f"@{handle} on X"
                title = f"@{handle}"
                scraping_failed = True
                capture_mode = "url_only"
        except Exception:
            # Clean fallback - just the handle
            text = f"@{handle} on X"
            title = f"@{handle}"
            scraping_failed = True
            capture_mode = "url_only"
        
        author = handle
    
    # Step 2: Create bookmark
    bookmark_id = stable_bookmark_id(url, text)
    timestamp = utc_now_iso()
    
    bookmark_data = {
        "id": bookmark_id,
        "source": "x",
        "url": url,
        "text": text,
        "title": title,
        "note": "Auto-captured from X via Forger agent" + (" (scraping blocked, URL-only)" if scraping_failed else ""),
        "author": author,
        "created_at": timestamp,
        "bookmarked_at": timestamp,
        "tags": ["general"],
        "raw_payload": {
            "ingestion_channel": "forger",
            "capture_mode": capture_mode,
            "scraped_via": "playwright" if not scraping_failed else None,
            "scraping_failed": scraping_failed
        }
    }
    
    # Step 3: Check for duplicate
    bookmarks = load_bookmarks()
    existing_urls = set()
    for b in bookmarks:
        if hasattr(b, 'url'):
            existing_urls.add(b.url)
        elif isinstance(b, dict):
            existing_urls.add(b.get('url'))
    
    if url in existing_urls:
        print(f"DUPLICATE: Bookmark with URL {url} already exists")
        return False, "DUPLICATE", None, None
    
    existing_ids = set()
    for b in bookmarks:
        if hasattr(b, 'id'):
            existing_ids.add(b.id)
        elif isinstance(b, dict):
            existing_ids.add(b.get('id'))
    
    if bookmark_id in existing_ids:
        print(f"DUPLICATE: Bookmark ID {bookmark_id} already exists")
        return False, "DUPLICATE", None, None
    
    # Step 4: Save bookmark
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
    
    bookmarks.insert(0, bookmark)
    save_bookmarks(bookmarks)
    print(f"✅ Saved bookmark: {bookmark.id}")
    
    # Step 5: DeepSeek analysis
    print("🧠 Running DeepSeek analysis...")
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
            "worth_score": deepseek_result.get('priority_score', 5.0),
            "effort_score": 3.0,
            "priority_score": deepseek_result.get('priority_score', 5.0),
            "recommendation_bucket": deepseek_result.get('bucket', 'archive'),
            "analysis_source": "deepseek",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        print(f"✅ Analysis complete - Bucket: {analysis['recommendation_bucket']}, Priority: {analysis['priority_score']}")
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
    
    # Step 6: Save analysis
    existing = load_analysis_results()
    existing = [a for a in existing if (a.bookmark_id if hasattr(a, 'bookmark_id') else a.get('bookmark_id')) != bookmark.id]
    
    existing_dicts = []
    for a in existing:
        if hasattr(a, 'to_dict'):
            existing_dicts.append(a.to_dict())
        elif isinstance(a, dict):
            existing_dicts.append(a)
        else:
            existing_dicts.append({
                'bookmark_id': a.bookmark_id,
                'summary': a.summary,
                'recommendation_reason': a.recommendation_reason,
                'key_insights': a.key_insights,
                'scoring_inputs': {
                    'relevance': a.scoring_inputs.relevance,
                    'practical_value': a.scoring_inputs.practical_value,
                    'actionability': a.scoring_inputs.actionability,
                    'stage_fit': a.scoring_inputs.stage_fit,
                    'novelty': a.scoring_inputs.novelty,
                    'excitement': a.scoring_inputs.excitement,
                    'difficulty': a.scoring_inputs.difficulty,
                    'time_cost': a.scoring_inputs.time_cost,
                },
                'worth_score': a.worth_score,
                'effort_score': a.effort_score,
                'priority_score': a.priority_score,
                'recommendation_bucket': a.recommendation_bucket,
                'analysis_source': a.analysis_source,
                'analyzed_at': a.analyzed_at,
            })
    
    existing_dicts.append(analysis)
    
    with open('/home/ubuntu/RolloForge/data/analysis_results.json', 'w') as f:
        json.dump(existing_dicts, f, indent=2)
    
    print(f"✅ Saved analysis to analysis_results.json")
    
    # Step 7: Sync to web dashboard
    try:
        from web.lib.copy_data import main as copy_data
        copy_data()
        print("✅ Synced to web dashboard")
    except Exception as e:
        print(f"⚠️ Web sync failed: {e}")
    
    # Step 8: Git push
    try:
        from rolloforge.git_auto import git_auto_push
        git_auto_push(bookmark.title)
        print("✅ Pushed to GitHub")
    except Exception as e:
        print(f"⚠️ Git push failed: {e}")
    
    return True, "SUCCESS", bookmark, analysis

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_x_dynamic.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    success, message, bookmark, analysis = process_x_url(url)
    
    if success and bookmark and analysis:
        result = {
            "status": "success",
            "bookmark_id": bookmark.id,
            "title": bookmark.title,
            "bucket": analysis["recommendation_bucket"],
            "priority_score": analysis["priority_score"],
            "worth_score": analysis["worth_score"],
            "effort_score": analysis["effort_score"],
            "tags": bookmark.tags,
        }
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({"status": "error", "message": message}, indent=2))
