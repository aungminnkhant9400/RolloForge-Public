#!/usr/bin/env python3
"""
Backfill tags and personalized scoring for all existing analyses.

This script:
1. Loads all bookmarks and analyses
2. Copies tags from bookmarks to their matching analyses
3. Re-runs personalized scoring on all analyses
4. Saves updated analyses back to storage
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Add RolloForge to path
sys.path.insert(0, "/home/ubuntu/RolloForge")

from rolloforge.storage import load_bookmarks, load_analysis_results, save_analysis_results
from rolloforge.personalized_scoring import personalize_scores
from rolloforge.priority_profile import load_profile

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def backfill_tags_and_scoring():
    """Backfill tags and personalized scoring for all analyses."""
    
    LOGGER.info("Loading data...")
    bookmarks = load_bookmarks()
    analyses = load_analysis_results()
    profile = load_profile()
    
    LOGGER.info(f"Loaded {len(bookmarks)} bookmarks, {len(analyses)} analyses")
    
    bookmark_map = {b.id: b for b in bookmarks}
    
    updated_count = 0
    tags_backfilled = 0
    scoring_updated = 0
    bucket_changes = 0
    
    updated_analyses = []
    
    for analysis in analyses:
        bid = analysis.bookmark_id
        bookmark = bookmark_map.get(bid)
        
        if not bookmark:
            LOGGER.warning(f"No bookmark found for analysis {bid}")
            updated_analyses.append(analysis)
            continue
        
        changed = False
        
        # Backfill tags from bookmark
        if bookmark.tags and (not analysis.tags or len(analysis.tags) == 0):
            analysis.tags = bookmark.tags
            tags_backfilled += 1
            changed = True
            LOGGER.info(f"Backfilled tags for {bid}: {bookmark.tags}")
        
        # Re-run personalized scoring
        ds_analysis = {
            "worth_score": analysis.worth_score,
            "priority_score": analysis.priority_score,
            "effort_score": analysis.effort_score,
            "recommendation_bucket": analysis.recommendation_bucket,
        }
        
        result = personalize_scores(
            bookmark_text=bookmark.text,
            bookmark_title=bookmark.title or "",
            bookmark_url=bookmark.url,
            tags=analysis.tags or bookmark.tags or [],
            deepseek_analysis=ds_analysis,
            profile=profile,
        )
        
        # Update analysis with personalized scores
        old_bucket = analysis.personalized_bucket or analysis.recommendation_bucket
        new_bucket = result["personalized_bucket"]
        
        analysis.personalized_worth_score = result["personalized_worth_score"]
        analysis.personalized_priority_score = result["personalized_priority_score"]
        analysis.personalized_bucket = result["personalized_bucket"]
        analysis.personalized_why = result["personalized_why"]
        analysis.original_worth_score = result["original_worth_score"]
        analysis.original_priority_score = result["original_priority_score"]
        analysis.original_bucket = result["original_bucket"]
        analysis.alignment_score = result["alignment_score"]
        
        if old_bucket != new_bucket:
            bucket_changes += 1
            LOGGER.info(f"Bucket change for {bid}: {old_bucket} -> {new_bucket} | {result['personalized_why'][:80]}")
        
        if result.get("worth_adjustment") or result.get("priority_adjustment"):
            scoring_updated += 1
        
        updated_analyses.append(analysis)
        
        if changed or old_bucket != new_bucket:
            updated_count += 1
    
    LOGGER.info(f"\nBackfill complete:")
    LOGGER.info(f"  Tags backfilled: {tags_backfilled}")
    LOGGER.info(f"  Scoring updated: {scoring_updated}")
    LOGGER.info(f"  Bucket changes: {bucket_changes}")
    LOGGER.info(f"  Total updated: {updated_count}")
    
    # Save updated analyses
    LOGGER.info("Saving updated analyses...")
    save_analysis_results(updated_analyses)
    LOGGER.info("Done!")
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"BACKFILL SUMMARY")
    print(f"{'='*50}")
    print(f"Total analyses: {len(analyses)}")
    print(f"Tags backfilled: {tags_backfilled}")
    print(f"Scoring updated: {scoring_updated}")
    print(f"Bucket changes: {bucket_changes}")
    print(f"{'='*50}")


if __name__ == "__main__":
    backfill_tags_and_scoring()
