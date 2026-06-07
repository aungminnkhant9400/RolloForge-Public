from __future__ import annotations

import logging
from typing import Any

from config.settings import Settings
from rolloforge.models import AnalysisResult, Bookmark, ScoringInputs
from rolloforge.scoring import auto_score_bookmark, score_analysis
from rolloforge.utils import compact_text, safe_list, utc_now_iso


LOGGER = logging.getLogger(__name__)


def analyze_bookmark(bookmark: Bookmark, settings: Settings) -> AnalysisResult:
    """
    Analyze a bookmark using the new auto-scoring system.
    Scores are calculated based on user's specific criteria:
    - OpenClaw prioritization
    - Source credibility (Karpathy, etc.)
    - Actionability with lazy+pickup-when-popular adjustment
    """
    # Auto-calculate all scoring inputs
    inputs = auto_score_bookmark(
        text=bookmark.text,
        author=bookmark.author,
        tags=bookmark.tags,
        url=bookmark.url
    )
    
    # Determine if OpenClaw-related for bucket assignment
    combined = f"{bookmark.text.lower()} {' '.join(bookmark.tags).lower()}"
    is_openclaw_related = "openclaw" in combined or "claude code" in combined
    
    # Calculate final scores and bucket
    worth_score, effort_score, priority_score, bucket = score_analysis(
        inputs, is_openclaw_related
    )
    
    # Generate insights based on scores
    insights = _generate_insights(bookmark, inputs, worth_score, priority_score)
    
    return AnalysisResult(
        bookmark_id=bookmark.id,
        summary=_generate_summary(bookmark),
        recommendation_reason=_generate_recommendation_reason(inputs, bucket, is_openclaw_related),
        key_insights=insights,
        scoring_inputs=inputs,
        worth_score=worth_score,
        effort_score=effort_score,
        priority_score=priority_score,
        recommendation_bucket=bucket,
        analysis_source="llm_auto_scored",
        analyzed_at=utc_now_iso(),
    )


def _generate_summary(bookmark: Bookmark) -> str:
    """Generate a meaningful summary from bookmark text.
    
    Analyzes content to extract key points, not just copy first sentence.
    """
    text = bookmark.text.strip()
    if not text:
        return "No content available."
    
    # For tweets/posts, extract the core message
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return "No content available."
    
    # Get main content (first substantial line)
    main_text = lines[0]
    
    # Remove URLs for cleaner summary
    import re
    clean_text = re.sub(r'https?://\S+', '', main_text).strip()
    
    # For Chinese or other non-ASCII, handle differently
    is_non_ascii = any(ord(c) > 127 for c in clean_text[:50])
    
    if is_non_ascii:
        # For Chinese/Japanese/etc, take first meaningful segment
        # Look for natural break points
        for punct in ['。', '？', '！', '. ', '? ', '! ']:
            idx = clean_text[:200].find(punct)
            if idx > 20:
                summary = clean_text[:idx + 1].strip()
                break
        else:
            # No punctuation found, take up to 150 chars at word boundary
            if len(clean_text) > 150:
                summary = clean_text[:150].rsplit(' ', 1)[0] + '...'
            else:
                summary = clean_text
    else:
        # For English, extract key message
        sentences = clean_text.split('. ')
        
        # Try to find a complete thought (not too short, not too long)
        best_sentence = None
        for sent in sentences:
            sent = sent.strip()
            if 30 < len(sent) < 200:
                best_sentence = sent
                break
        
        if best_sentence:
            summary = best_sentence
            if not summary.endswith('.'):
                summary += '.'
        else:
            # Fallback to first sentence truncated
            summary = clean_text[:150].strip()
            if len(summary) >= 150:
                summary = summary.rsplit(' ', 1)[0] + '...'
            elif not summary.endswith('.'):
                summary += '.'
    
    # Final cleanup
    summary = re.sub(r'\s+', ' ', summary).strip()
    
    return summary if summary else "Content summary unavailable."


def _generate_recommendation_reason(
    inputs: ScoringInputs, 
    bucket: str, 
    is_openclaw_related: bool
) -> str:
    """Generate a personalized recommendation reason."""
    reasons = []
    
    if is_openclaw_related:
        reasons.append("Directly related to your OpenClaw system build.")
    
    if inputs.relevance >= 9:
        reasons.append("High relevance to your current priorities.")
    elif inputs.relevance >= 7:
        reasons.append("Relevant to your multi-agent interests.")
    
    if inputs.practical_value >= 8:
        reasons.append("Contains actionable implementation details.")
    
    if inputs.actionability >= 8:
        reasons.append("Ready to try when you have time.")
    elif inputs.actionability >= 6:
        reasons.append("Good candidate for when this becomes popular.")
    
    if inputs.novelty >= 8:
        reasons.append("Novel approach you haven't seen before.")
    
    bucket_reasons = {
        "test_this_week": "High priority for your current build phase.",
        "build_later": "Save for after current priorities.",
        "archive": "Reference material for future projects.",
        "ignore": "Low priority given your current focus.",
    }
    reasons.append(bucket_reasons.get(bucket, ""))
    
    return " ".join(filter(None, reasons))


def _generate_insights(
    bookmark: Bookmark, 
    inputs: ScoringInputs,
    worth_score: float,
    priority_score: float
) -> list[str]:
    """Generate key insights based on scoring."""
    insights = [
        f"Source: {bookmark.author or 'unknown'}",
        f"Relevance: {inputs.relevance:.1f}/10",
        f"Actionability: {inputs.actionability:.1f}/10 (with lazy+popular bonus)",
    ]
    
    if inputs.novelty >= 8:
        insights.append("Novel concept - first time seeing this approach")
    
    if inputs.relevance >= 9:
        insights.append("Directly aligned with OpenClaw build priorities")
    
    if priority_score >= 6:
        insights.append("High priority - consider trying this week")
    elif priority_score >= 4:
        insights.append("Medium priority - good for build-later queue")
    
    return insights[:5]


def normalize_analysis_payload(bookmark: Bookmark, payload: dict[str, Any], analysis_source: str) -> AnalysisResult:
    """Normalize an external analysis payload (for backward compatibility)."""
    inputs = ScoringInputs.from_dict(payload.get("scoring_inputs", {}))
    combined = f"{bookmark.text.lower()} {' '.join(bookmark.tags).lower()}"
    is_openclaw_related = "openclaw" in combined or "claude code" in combined
    
    worth_score, effort_score, priority_score, bucket = score_analysis(
        inputs, is_openclaw_related
    )
    
    return AnalysisResult(
        bookmark_id=bookmark.id,
        summary=compact_text(str(payload.get("summary", bookmark.text)), limit=220),
        recommendation_reason=compact_text(
            str(payload.get("recommendation_reason", "No recommendation rationale supplied.")),
            limit=260,
        ),
        key_insights=safe_list(payload.get("key_insights"))[:5],
        scoring_inputs=inputs,
        worth_score=worth_score,
        effort_score=effort_score,
        priority_score=priority_score,
        recommendation_bucket=bucket,
        analysis_source=analysis_source,
        analyzed_at=utc_now_iso(),
    )


def analyze_pending_bookmarks(
    bookmarks: list[Bookmark],
    existing_ids: set[str],
    settings: Settings,
    limit: int | None = None,
    force_all: bool = False,
) -> list[AnalysisResult]:
    """Analyze pending bookmarks with the new scoring system."""
    pending = bookmarks if force_all else [bookmark for bookmark in bookmarks if bookmark.id not in existing_ids]
    if limit is not None:
        pending = pending[:limit]
    LOGGER.info("Analyzing %s bookmark(s) with auto-scoring.", len(pending))
    return [analyze_bookmark(bookmark, settings) for bookmark in pending]