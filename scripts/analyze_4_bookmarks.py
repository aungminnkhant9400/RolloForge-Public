#!/usr/bin/env python3
"""Analyze specific bookmarks with DeepSeek and append results."""
import json
import os
import sys
from datetime import datetime, timezone

# Add RolloForge to path
sys.path.insert(0, '/home/ubuntu/RolloForge')

from rolloforge.deepseek_analysis import analyze_with_deepseek

# The 4 bookmarks to analyze
BOOKMARK_IDS = [
    "bookmark_milkroadai_2043906896285901183",
    "bookmark_code_rams_2044185657128649115",
    "bookmark_vtrivedy10_2043427918127513836",
    "bookmark_andrewyng_linkedin_7449507590927196160"
]

def load_bookmarks():
    with open('/home/ubuntu/RolloForge/data/bookmarks_raw.json', 'r') as f:
        return json.load(f)

def load_analysis_results():
    try:
        with open('/home/ubuntu/RolloForge/data/analysis_results.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_analysis_results(results):
    with open('/home/ubuntu/RolloForge/data/analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)

def find_bookmark(bookmarks, bookmark_id):
    for bm in bookmarks:
        if bm.get('id') == bookmark_id:
            return bm
    return None

def analyze_bookmark(bookmark):
    """Analyze a single bookmark with DeepSeek."""
    text = bookmark.get('text', '')
    title = bookmark.get('title', '')
    url = bookmark.get('url', '')
    
    print(f"\n🔍 Analyzing: {title[:60]}...")
    print(f"   ID: {bookmark['id']}")
    
    result = analyze_with_deepseek(text, title, url)
    
    if result:
        # Build analysis result in the expected format
        analysis = {
            "bookmark_id": bookmark['id'],
            "summary": result.get('summary', 'Analysis pending'),
            "recommendation_reason": result.get('recommendation_reason', ''),
            "key_insights": result.get('key_insights', []),
            "scoring_inputs": {
                "relevance": result.get('relevance', 5.0),
                "practical_value": result.get('practical_value', 5.0),
                "actionability": result.get('actionability', 5.0),
                "stage_fit": result.get('stage_fit', 5.0),
                "novelty": result.get('novelty', 5.0),
                "excitement": result.get('excitement', 5.0),
                "difficulty": result.get('difficulty', 5.0),
                "time_cost": result.get('time_cost', 5.0)
            },
            "worth_score": result.get('worth_score', 5.0),
            "effort_score": result.get('effort_score', 5.0),
            "priority_score": result.get('priority_score', 5.0),
            "recommendation_bucket": result.get('recommendation_bucket', 'archive'),
            "analysis_source": "deepseek",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "confidence": None,
            "difficulty_reason": None,
            "next_action": None
        }
        print(f"   ✅ Priority: {analysis['priority_score']:.1f} | Bucket: {analysis['recommendation_bucket']}")
        return analysis
    else:
        print(f"   ❌ DeepSeek analysis failed")
        return None

def main():
    print("=" * 60)
    print("DeepSeek Bookmark Analysis")
    print("=" * 60)
    
    # Load data
    bookmarks = load_bookmarks()
    existing_results = load_analysis_results()
    
    # Filter out existing results for our target bookmarks
    existing_ids = {r.get('bookmark_id') for r in existing_results}
    target_ids = [bid for bid in BOOKMARK_IDS if bid not in existing_ids]
    
    print(f"\n📚 Total bookmarks: {len(bookmarks)}")
    print(f"📊 Existing analyses: {len(existing_results)}")
    print(f"🎯 To analyze: {len(target_ids)}")
    
    new_results = []
    
    for bookmark_id in target_ids:
        bookmark = find_bookmark(bookmarks, bookmark_id)
        if not bookmark:
            print(f"\n⚠️  Bookmark not found: {bookmark_id}")
            continue
        
        analysis = analyze_bookmark(bookmark)
        if analysis:
            new_results.append(analysis)
    
    # Append new results
    if new_results:
        all_results = existing_results + new_results
        save_analysis_results(all_results)
        print(f"\n✅ Saved {len(new_results)} new analyses")
        print(f"📁 Total analyses: {len(all_results)}")
    else:
        print("\n⚠️  No new analyses to save")
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

if __name__ == "__main__":
    main()
