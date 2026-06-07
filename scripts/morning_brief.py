#!/usr/bin/env python3
"""
Generate morning brief - concise summary of top priority bookmarks.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rolloforge.storage import load_bookmarks, load_analysis_results


def effective_bucket(analysis):
    return analysis.personalized_bucket or analysis.recommendation_bucket


def effective_priority(analysis):
    return analysis.personalized_priority_score if analysis.personalized_priority_score is not None else analysis.priority_score


def generate_morning_brief() -> str:
    """Generate concise morning brief text."""
    bookmarks = load_bookmarks()
    analysis_results = load_analysis_results()
    
    # Create map
    analysis_map = {a.bookmark_id: a for a in analysis_results}
    
    # Get test_this_week items (highest priority)
    test_this_week = [
        (b, analysis_map.get(b.id)) 
        for b in bookmarks 
        if analysis_map.get(b.id) and effective_bucket(analysis_map.get(b.id)) == "test_this_week"
    ]
    
    # Get build_later items
    build_later = [
        (b, analysis_map.get(b.id)) 
        for b in bookmarks 
        if analysis_map.get(b.id) and effective_bucket(analysis_map.get(b.id)) == "build_later"
    ]
    
    lines = ["🌅 RolloForge Morning Brief", "=" * 40, ""]
    
    if test_this_week:
        lines.append(f"⚡ {len(test_this_week)} items to test this week:")
        lines.append("")
        for bookmark, analysis in sorted(test_this_week, key=lambda x: effective_priority(x[1]), reverse=True):
            lines.append(f"• {bookmark.text[:60]}...")
            lines.append(f"  Worth: {analysis.worth_score:.1f} | Priority: {effective_priority(analysis):.1f}")
            lines.append(f"  → {analysis.summary[:80]}...")
            lines.append("")
    else:
        lines.append("⚡ No 'test this week' items.")
        lines.append("")
    
    if build_later:
        lines.append(f"📚 {len(build_later)} items in backlog (build later)")
        lines.append("")
    
    lines.append("=" * 40)
    lines.append("Say 'bmreport' for full HTML report")
    
    return "\n".join(lines)


if __name__ == "__main__":
    brief = generate_morning_brief()
    print(brief)