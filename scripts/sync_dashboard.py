#!/usr/bin/env python3
"""Sync dashboard data files from source to web/lib/.

This ensures the dashboard always shows current bookmarks.
Run this after every bookmark save.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Paths
DATA_DIR = Path("/home/ubuntu/RolloForge/data")
WEB_LIB_DIR = Path("/home/ubuntu/RolloForge/web/lib")


def sync_dashboard_data() -> bool:
    """Copy bookmarks and analysis files to dashboard directory."""
    try:
        # Copy bookmarks
        src_bookmarks = DATA_DIR / "bookmarks_raw.json"
        dst_bookmarks = WEB_LIB_DIR / "data.json"
        shutil.copy2(src_bookmarks, dst_bookmarks)
        
        # Copy analysis
        src_analysis = DATA_DIR / "analysis_results.json"
        dst_analysis = WEB_LIB_DIR / "analysis.json"
        shutil.copy2(src_analysis, dst_analysis)
        
        # Update stats summary with current timestamp
        with open(src_bookmarks) as f:
            bookmarks = json.load(f)
        
        # Load analysis results to compute bucket counts
        with open(src_analysis) as f:
            analyses = json.load(f)
        
        # Create analysis lookup by bookmark_id
        analysis_by_id = {a['bookmark_id']: a for a in analyses}
        
        from collections import Counter
        # Get buckets from analysis results, prefer personalized_bucket when available
        def get_bucket(a):
            return a.get('personalized_bucket') or a.get('recommendation_bucket', 'NO_BUCKET')
        
        buckets = Counter(
            get_bucket(analysis_by_id.get(b['id'], {}))
            for b in bookmarks
        )
        
        # Count bookmarks with missing analysis
        missing_analysis = sum(
            1 for b in bookmarks 
            if b['id'] not in analysis_by_id
        )
        
        stats = {
            "total_bookmarks": len(bookmarks),
            "total_analyses": len(analyses),
            "buckets": dict(buckets),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "data_quality": {
                "missing_analyses": missing_analysis, 
                "orphan_analyses": 0, 
                "duplicates": 0
            }
        }
        
        with open(DATA_DIR / "stats_summary.json", 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"✅ Dashboard synced: {len(bookmarks)} bookmarks")
        print(f"   Buckets: {dict(buckets)}")
        return True
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    success = sync_dashboard_data()
    sys.exit(0 if success else 1)
