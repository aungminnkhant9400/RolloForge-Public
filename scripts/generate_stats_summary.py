#!/usr/bin/env python3
"""
Generate stats summary for RolloForge.

Loads analysis_results.json and bookmarks_raw.json, computes bucket
distribution and data quality metrics, and writes stats_summary.json.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path("/home/ubuntu/RolloForge")
DATA_DIR = PROJECT_ROOT / "data"


def main() -> None:
    bookmarks_path = DATA_DIR / "bookmarks_raw.json"
    analyses_path = DATA_DIR / "analysis_results.json"
    output_path = DATA_DIR / "stats_summary.json"

    # Load bookmarks
    with open(bookmarks_path, "r", encoding="utf-8") as f:
        bookmarks = json.load(f)
    total_bookmarks = len(bookmarks)

    # Load analyses
    with open(analyses_path, "r", encoding="utf-8") as f:
        analyses = json.load(f)
    total_analyses = len(analyses)

    # Compute bucket distribution
    buckets: dict[str, int] = {}
    for analysis in analyses:
        bucket = analysis.get("bucket") or analysis.get("recommendation_bucket") or "unknown"
        buckets[bucket] = buckets.get(bucket, 0) + 1

    # Compute data quality metrics
    bookmark_ids = {bm.get("id") for bm in bookmarks}
    analysis_ids = {an.get("bookmark_id") for an in analyses}

    missing_analyses = len(bookmark_ids - analysis_ids)
    orphan_analyses = len(analysis_ids - bookmark_ids)

    # Duplicate detection (by id)
    seen_ids = set()
    duplicates = 0
    for bm in bookmarks:
        bm_id = bm.get("id")
        if bm_id in seen_ids:
            duplicates += 1
        seen_ids.add(bm_id)

    stats = {
        "total_bookmarks": total_bookmarks,
        "total_analyses": total_analyses,
        "buckets": buckets,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_quality": {
            "missing_analyses": missing_analyses,
            "orphan_analyses": orphan_analyses,
            "duplicates": duplicates,
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"✓ stats_summary.json generated: {total_bookmarks} bookmarks, {total_analyses} analyses, buckets={buckets}")


if __name__ == "__main__":
    main()
