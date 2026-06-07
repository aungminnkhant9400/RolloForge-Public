"""
Personalized Scoring Engine for RolloForge.

Takes a bookmark + DeepSeek analysis and adjusts scores based on Rollo's
actual priorities (from priority_profile.py). Generates a "why" explanation
so Rollo knows WHY a bookmark got its score.

Key concept: DeepSeek scores "is this generally useful?"
This module scores "is this useful for ROLLO specifically?"
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from rolloforge.priority_profile import load_profile
from rolloforge.utils import clamp_score

LOGGER = logging.getLogger(__name__)

# Minimum adjustment magnitude to bother explaining
MIN_ADJUSTMENT = 0.3


def _tokenize(text: str) -> list[str]:
    """Simple tokenization for keyword matching."""
    return re.findall(r'\b[a-zA-Z0-9][a-zA-Z0-9\-_]{1,30}\b', text.lower())


def compute_alignment(
    text: str,
    title: str,
    tags: list[str],
    url: str,
    profile: dict[str, Any]
) -> tuple[float, dict[str, Any]]:
    """
    Compute how well a bookmark aligns with Rollo's priorities.
    
    Returns:
        (alignment_score, alignment_detail)
        
    alignment_score: 0-10, how well this matches Rollo's priorities
    alignment_detail: breakdown of what matched
    """
    combined = f"{text.lower()} {title.lower()} {url.lower()} {' '.join(tags).lower()}"
    tokens = _tokenize(combined)
    token_set = set(tokens)

    projects = profile.get("projects", {})
    global_boosts = profile.get("global_boost_keywords", {})
    distractions = profile.get("distraction_keywords", {})

    matched_projects: list[dict] = []
    total_boost = 0.0
    best_match_weight = 0.0

    # Check each project's keywords
    for slug, proj in projects.items():
        proj_keywords = [kw.lower() for kw in proj["keywords"]]
        weight = proj["weight"]
        label = proj["label"]

        # Count keyword matches
        matches = []
        for kw in proj_keywords:
            if kw in combined:
                matches.append(kw)
            # Also check multi-word keywords
            elif ' ' in kw and kw in combined.lower():
                matches.append(kw)

        if matches:
            # Stronger match = more matches AND higher weight
            match_score = min(len(matches) * 1.5, weight)
            matched_projects.append({
                "project": slug,
                "label": label,
                "weight": weight,
                "matches": matches[:5],  # Top 5 matches
                "match_count": len(matches),
                "boost": round(match_score * 0.15, 2),  # Scale to 0-1.5 range
            })
            total_boost += match_score * 0.15
            best_match_weight = max(best_match_weight, weight)

    # Global keyword boosts (smaller than project matches)
    global_boost = 0.0
    global_matches = []
    for kw, boost in global_boosts.items():
        if kw in combined:
            global_boost += boost * 0.1
            global_matches.append(kw)

    total_boost += global_boost

    # Distraction penalties
    distraction_penalty = 0.0
    distraction_matches = []
    for kw, penalty in distractions.items():
        if kw in combined:
            distraction_penalty += abs(penalty) * 0.1
            distraction_matches.append(kw)

    total_boost -= distraction_penalty

    # Compute alignment score (base 5.0 ± adjustments)
    alignment_score = clamp_score(5.0 + total_boost)

    detail = {
        "matched_projects": matched_projects,
        "global_matches": global_matches,
        "distraction_matches": distraction_matches,
        "best_project": matched_projects[0]["label"] if matched_projects else None,
        "best_project_weight": best_match_weight,
        "total_keyword_matches": sum(p["match_count"] for p in matched_projects),
        "adjustment": round(total_boost, 2),
    }

    return alignment_score, detail


def generate_why(
    original_analysis: dict[str, Any],
    alignment_detail: dict[str, Any],
    worth_adjustment: float,
    priority_adjustment: float,
    bucket_changed: bool,
    original_bucket: str,
    new_bucket: str,
) -> str:
    """Generate a human-readable explanation of the scoring."""
    parts = []

    matched = alignment_detail.get("matched_projects", [])
    global_m = alignment_detail.get("global_matches", [])
    distract = alignment_detail.get("distraction_matches", [])

    # What did it match?
    if matched:
        top_projects = [m["label"] for m in matched[:2]]
        parts.append(f"Matches your priorities: {', '.join(top_projects)}")

    if global_m:
        parts.append(f"Contains high-signal terms: {', '.join(global_m[:3])}")

    if distract:
        parts.append(f"⚠ Distraction signals: {', '.join(distract[:3])}")

    # Score adjustments
    if abs(worth_adjustment) >= MIN_ADJUSTMENT:
        direction = "↑" if worth_adjustment > 0 else "↓"
        parts.append(f"Worth {direction}{abs(worth_adjustment):.1f}")

    if abs(priority_adjustment) >= MIN_ADJUSTMENT:
        direction = "↑" if priority_adjustment > 0 else "↓"
        parts.append(f"Priority {direction}{abs(priority_adjustment):.1f}")

    # Bucket change
    if bucket_changed:
        parts.append(f"Re-bucketed: {original_bucket} → {new_bucket}")

    if not parts:
        parts.append("No strong alignment with current priorities")

    return " • ".join(parts)


def personalize_scores(
    bookmark_text: str,
    bookmark_title: str,
    bookmark_url: str,
    tags: list[str],
    deepseek_analysis: dict[str, Any],
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Adjust bookmark scores based on Rollo's personal priorities.
    
    Args:
        bookmark_text: Full bookmark content
        bookmark_title: Bookmark title
        bookmark_url: Source URL
        tags: Current tags
        deepseek_analysis: Dict from DeepSeek (must have worth_score, priority_score, etc.)
        profile: Pre-loaded profile (loads from cache if None)
        
    Returns:
        Dict with adjusted scores, alignment info, and "why" explanation.
        Original scores are preserved as original_* fields.
    """
    raw_tags = [str(tag).strip().lower() for tag in (tags or []) if str(tag).strip()]
    if deepseek_analysis.get("analysis_source") == "deepseek_fallback" or any(
        tag in {"deepseek-failed", "review-manually", "analysis-failed"}
        for tag in raw_tags
    ):
        original_worth = float(deepseek_analysis.get("worth_score", 5.0))
        original_priority = float(deepseek_analysis.get("priority_score", 3.0))
        original_bucket = deepseek_analysis.get("recommendation_bucket", "archive")
        return {
            "personalized_worth_score": original_worth,
            "personalized_priority_score": original_priority,
            "personalized_bucket": original_bucket,
            "personalized_why": "DeepSeek failed — quarantined for manual review instead of promoting it.",
            "original_worth_score": original_worth,
            "original_priority_score": original_priority,
            "original_bucket": original_bucket,
            "alignment_score": None,
            "alignment_detail": {},
        }

    if profile is None:
        profile = load_profile()

    # Compute alignment
    alignment_score, alignment_detail = compute_alignment(
        bookmark_text, bookmark_title, tags, bookmark_url, profile
    )

    # Get original scores
    original_worth = float(deepseek_analysis.get("worth_score", 5.0))
    original_priority = float(deepseek_analysis.get("priority_score", 3.0))
    original_bucket = deepseek_analysis.get("recommendation_bucket", "archive")
    original_effort = float(deepseek_analysis.get("effort_score", 5.0))

    # Alignment adjustment factor
    # alignment_score is 0-10, centered at 5.
    # Scores > 5 = positive alignment → boost
    # Scores < 5 = poor alignment → penalty
    alignment_delta = (alignment_score - 5.0) / 5.0  # Range: -1.0 to +1.0

    # Apply to worth score (alignment affects how useful this is for Rollo)
    worth_adjustment = round(alignment_delta * 2.5, 1)  # Max ±2.5 adjustment
    adjusted_worth = clamp_score(original_worth + worth_adjustment)

    # Priority gets double the alignment effect (more sensitive to personal fit)
    priority_adjustment = round(alignment_delta * 3.0, 1)  # Max ±3.0 adjustment
    adjusted_priority = clamp_score(original_priority + priority_adjustment)

    # Determine new bucket — alignment can override
    new_bucket = original_bucket

    # Strong alignment can bump bucket UP
    if alignment_score >= 8.0:
        if original_bucket == "build_later":
            best_weight = alignment_detail.get("best_project_weight", 0)
            if best_weight >= 8.5:
                new_bucket = "test_this_week"
        elif original_bucket == "archive" and alignment_detail.get("total_keyword_matches", 0) >= 3:
            new_bucket = "build_later"

    # Poor alignment can bump bucket DOWN
    if alignment_score <= 2.5 and original_bucket == "test_this_week":
        best_weight = alignment_detail.get("best_project_weight", 0)
        if best_weight < 6.0:
            new_bucket = "build_later"
    elif alignment_score <= 2.0 and original_bucket == "build_later":
        if alignment_detail.get("total_keyword_matches", 0) == 0:
            new_bucket = "archive"

    bucket_changed = new_bucket != original_bucket

    # Generate explanation
    why = generate_why(
        deepseek_analysis,
        alignment_detail,
        worth_adjustment,
        priority_adjustment,
        bucket_changed,
        original_bucket,
        new_bucket,
    )

    result = {
        # Personalized scores
        "personalized_worth_score": adjusted_worth,
        "personalized_priority_score": adjusted_priority,
        "personalized_bucket": new_bucket,
        "personalized_why": why,
        
        # Original scores preserved
        "original_worth_score": original_worth,
        "original_priority_score": original_priority,
        "original_bucket": original_bucket,
        
        # Adjustment metadata
        "alignment_score": round(alignment_score, 1),
        "worth_adjustment": worth_adjustment,
        "priority_adjustment": priority_adjustment,
        "bucket_changed": bucket_changed,
        "alignment_detail": alignment_detail,
        
        # Profile version for traceability
        "profile_built_at": profile.get("built_at", "unknown"),
    }

    LOGGER.info(
        "Personalized: %s → worth %s→%s, priority %s→%s, bucket %s→%s | %s",
        bookmark_title[:50],
        original_worth, adjusted_worth,
        original_priority, adjusted_priority,
        original_bucket, new_bucket,
        why[:80],
    )

    return result


def rescore_all_bookmarks(dry_run: bool = True) -> dict[str, Any]:
    """
    Re-score all existing bookmarks with personalized scoring.
    
    Args:
        dry_run: If True, show changes without saving
        
    Returns:
        Summary of changes that would be made
    """
    from rolloforge.storage import load_bookmarks, load_analysis_results, save_analysis_results
    
    profile = load_profile()
    bookmarks = load_bookmarks()
    analyses = load_analysis_results()
    
    bookmark_map = {b.id: b for b in bookmarks}
    analysis_map = {a.bookmark_id: a for a in analyses}
    
    changes = []
    stats = {
        "total": len(analyses),
        "bucket_changes": 0,
        "worth_changed": 0,
        "priority_changed": 0,
        "bumped_up": 0,
        "bumped_down": 0,
    }
    
    updated_analyses = []
    
    for analysis in analyses:
        bid = analysis.bookmark_id
        bookmark = bookmark_map.get(bid)
        if not bookmark:
            continue
        
        # Get DeepSeek analysis as dict
        ds_analysis = {
            "worth_score": analysis.worth_score,
            "priority_score": analysis.priority_score,
            "effort_score": analysis.effort_score,
            "recommendation_bucket": analysis.recommendation_bucket,
        }
        
        # Run personalized scoring
        result = personalize_scores(
            bookmark_text=bookmark.text,
            bookmark_title=bookmark.title or "",
            bookmark_url=bookmark.url,
            tags=bookmark.tags,
            deepseek_analysis=ds_analysis,
            profile=profile,
        )
        
        # Update analysis with personalized scores
        analysis.personalized_worth_score = result["personalized_worth_score"]
        analysis.personalized_priority_score = result["personalized_priority_score"]
        analysis.personalized_bucket = result["personalized_bucket"]
        analysis.personalized_why = result["personalized_why"]
        analysis.original_worth_score = result["original_worth_score"]
        analysis.original_priority_score = result["original_priority_score"]
        analysis.original_bucket = result["original_bucket"]
        analysis.alignment_score = result["alignment_score"]
        
        if result["bucket_changed"]:
            stats["bucket_changes"] += 1
            if result["personalized_bucket"] in ("test_this_week",) and result["original_bucket"] not in ("test_this_week",):
                stats["bumped_up"] += 1
            elif result["original_bucket"] in ("test_this_week",) and result["personalized_bucket"] not in ("test_this_week",):
                stats["bumped_down"] += 1
            
            changes.append({
                "bookmark_id": bid,
                "title": bookmark.title or "Untitled",
                "original_bucket": result["original_bucket"],
                "new_bucket": result["personalized_bucket"],
                "why": result["personalized_why"],
            })
        
        if abs(result["worth_adjustment"]) >= MIN_ADJUSTMENT:
            stats["worth_changed"] += 1
        if abs(result["priority_adjustment"]) >= MIN_ADJUSTMENT:
            stats["priority_changed"] += 1
        
        updated_analyses.append(analysis)
    
    if not dry_run and updated_analyses:
        save_analysis_results(updated_analyses)
        LOGGER.info("Saved %d updated analyses", len(updated_analyses))
    
    return {
        "stats": stats,
        "changes": changes,
        "profile_built_at": profile.get("built_at", "unknown"),
        "dry_run": dry_run,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    
    # Test with a sample
    profile = load_profile()
    print(f"Profile: {profile['stats']}")
    print()

    # Test alignment
    test_bookmarks = [
        ("nnU-Net v2 released with improved tumor segmentation accuracy on BraTS dataset", "medical imaging test", "https://github.com/nnunet", ["medical-imaging"]),
        ("New NFT collection drops tomorrow on Solana", "nft test", "https://x.com/nftdrops", ["nft"]),
        ("Kimi K2.6 beats Claude on LiveBench coding benchmark", "model test", "https://x.com/kimi", ["llm"]),
        ("How I built a million-dollar SaaS with AI agents and OpenClaw", "agent test", "https://x.com/builder", ["agents"]),
    ]
    
    for text, title, url, tags in test_bookmarks:
        ds = {"worth_score": 7.0, "priority_score": 5.0, "effort_score": 3.0, "recommendation_bucket": "build_later"}
        result = personalize_scores(text, title, url, tags, ds, profile)
        print(f"📌 {title}")
        print(f"   Alignment: {result['alignment_score']} | Worth: {result['original_worth_score']}→{result['personalized_worth_score']} | Priority: {result['original_priority_score']}→{result['personalized_priority_score']} | Bucket: {result['original_bucket']}→{result['personalized_bucket']}")
        print(f"   Why: {result['personalized_why']}")
        print()
