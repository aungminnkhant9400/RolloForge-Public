#!/usr/bin/env python3
"""
Save a bookmark and its analysis directly.
Called by Garfis after manual LLM analysis.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BOOKMARKS_RAW_PATH, ANALYSIS_RESULTS_PATH
from rolloforge.models import Bookmark, AnalysisResult
from rolloforge.storage import load_bookmarks, save_bookmarks, load_analysis_results, upsert_analysis_results


def sync_dashboard() -> bool:
    """Auto-sync dashboard data files after bookmark save."""
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "sync_dashboard.py")],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✅ Dashboard auto-synced")
            return True
        else:
            print(f"⚠️ Dashboard sync warning: {result.stderr}")
            return False
    except Exception as e:
        print(f"⚠️ Dashboard sync failed (non-critical): {e}")
        return False


def save_bookmark_and_analysis(bookmark_dict: dict, analysis_dict: dict) -> None:
    """Save a bookmark and its analysis to JSON files. Skip if URL already exists."""
    # Load existing
    existing_bookmarks = load_bookmarks()
    existing_analysis = load_analysis_results()
    
    # Check for duplicate URL
    new_url = bookmark_dict.get('url', '')
    existing_urls = {b.url for b in existing_bookmarks}
    
    if new_url in existing_urls:
        print(f"DUPLICATE: URL already saved - {new_url[:60]}...")
        return
    
    # Create models
    bookmark = Bookmark.from_dict(bookmark_dict)
    analysis = AnalysisResult.from_dict(analysis_dict)
    
    # Merge and save bookmark
    bookmark_ids = {b.id for b in existing_bookmarks}
    if bookmark.id not in bookmark_ids:
        existing_bookmarks.append(bookmark)
    else:
        # Replace existing
        existing_bookmarks = [b if b.id != bookmark.id else bookmark for b in existing_bookmarks]
    save_bookmarks(existing_bookmarks)
    
    # Merge and save analysis
    upsert_analysis_results(existing_analysis, [analysis])
    
    print(f"SAVED: {bookmark.id}")
    
    # Auto-sync dashboard data
    sync_dashboard()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: save_bookmark.py <bookmark_json> <analysis_json>")
        sys.exit(1)
    
    bookmark_json = sys.argv[1]
    analysis_json = sys.argv[2]
    
    bookmark_dict = json.loads(bookmark_json)
    analysis_dict = json.loads(analysis_json)
    
    save_bookmark_and_analysis(bookmark_dict, analysis_dict)