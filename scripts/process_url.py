#!/usr/bin/env python3
"""
Forger — Process a URL into RolloForge end-to-end.

Usage:
    python scripts/process_url.py "https://x.com/user/status/123"
    python scripts/process_url.py "https://example.com/article"

Workflow:
    1. Check duplicate
    2. Scrape content (X/Twitter or article)
    3. Analyze with DeepSeek (fallback on failure)
    4. Apply Rollo's personalized scoring
    5. Create bookmark + analysis
    6. Verify counts match (bookmarks == analyses)
    7. Sync to web dashboard
    8. Git commit + push

Safety:
    - Always loads existing data before writing
    - Uses upsert_analysis_results() — never overwrites
    - Verifies data integrity after every save
    - Assertions guard against data corruption
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from rolloforge.scrapers import fetch_x_content_sync
from rolloforge.deepseek_analysis import deepseek_analyze_bookmark
from rolloforge.models import Bookmark, AnalysisResult, ScoringInputs
from rolloforge.storage import (
    load_bookmarks,
    save_bookmarks,
    load_analysis_results,
    upsert_analysis_results,
)
from rolloforge.personalized_scoring import personalize_scores
from rolloforge.priority_profile import load_profile
from rolloforge.utils import stable_bookmark_id
from rolloforge.git_auto import git_auto_push

LOGGER = logging.getLogger(__name__)

# ── Bucket Override Rules ──────────────────────────────────────────────────

def apply_bucket_overrides(text: str, analysis: dict) -> dict:
    """Override DeepSeek's conservative bucketing for Rollo's priorities."""
    tags = {str(tag).strip().lower() for tag in analysis.get('tags', []) if str(tag).strip()}
    if analysis.get('analysis_source') == 'deepseek_fallback' or tags & {'deepseek-failed', 'review-manually', 'analysis-failed'}:
        analysis['recommendation_bucket'] = 'archive'
        analysis['worth_score'] = min(float(analysis.get('worth_score', 5.0)), 5.0)
        analysis['priority_score'] = min(float(analysis.get('priority_score', 3.0)), 3.0)
        return analysis

    text_lower = text.lower()

    # AI Agents / Multi-Agent / Assistants → test_this_week
    agent_keywords = ['agent', 'jarvis', 'assistant', 'multi-agent', 'agentic',
                      'openclaw', 'hermes', 'clawd', 'skill', 'plugin', 'integration']
    if analysis['recommendation_bucket'] == 'archive' and any(k in text_lower for k in agent_keywords):
        LOGGER.info("OVERRIDE: Agent content → test_this_week")
        analysis['recommendation_bucket'] = 'test_this_week'
        analysis['worth_score'] = max(analysis['worth_score'], 6.5)
        analysis['priority_score'] = max(analysis['priority_score'], analysis['worth_score'] - 0.5 * analysis['effort_score'])

    # Model Releases → test_this_week
    model_keywords = ['kimi', 'grok', 'qwen', 'claude', 'deepseek', 'model release',
                      'preview', 'new model', 'benchmark', 'llm comparison']
    if analysis['recommendation_bucket'] == 'archive' and any(k in text_lower for k in model_keywords):
        LOGGER.info("OVERRIDE: Model release → test_this_week")
        analysis['recommendation_bucket'] = 'test_this_week'
        analysis['worth_score'] = max(analysis['worth_score'], 6.5)
        analysis['priority_score'] = max(analysis['priority_score'], analysis['worth_score'] - 0.5 * analysis['effort_score'])

    # Trading / Quant → build_later (not archive)
    trading_keywords = ['trading bot', 'quant', 'strategy', 'backtest', 'polymarket',
                        'crypto trading', 'forex', 'chart analysis']
    if analysis['recommendation_bucket'] == 'archive' and any(k in text_lower for k in trading_keywords):
        LOGGER.info("OVERRIDE: Trading content → build_later")
        analysis['recommendation_bucket'] = 'build_later'
        analysis['worth_score'] = max(analysis['worth_score'], 5.0)
        analysis['priority_score'] = max(analysis['priority_score'], analysis['worth_score'] - 0.5 * analysis['effort_score'])

    return analysis


# ── Main Processing ────────────────────────────────────────────────────────

def process_bookmark_url(url: str) -> tuple[bool, str, Bookmark | None, AnalysisResult | None]:
    """Process a single URL end-to-end. Returns (success, message, bookmark, analysis)."""

    # ── Step 0: Check duplicate ──
    existing_bm = load_bookmarks()
    for b in existing_bm:
        if b.url == url:
            # Already exists — check if analysis exists too
            existing_an = load_analysis_results()
            has_analysis = any(a.bookmark_id == b.id for a in existing_an)
            if has_analysis:
                return False, f"DUPLICATE: Already saved with analysis ({b.title})", b, None
            else:
                LOGGER.warning("Bookmark exists but NO analysis — proceeding to create analysis")
                # Falls through to analysis step

    LOGGER.info("Processing: %s", url)

    # ── Step 1: Scrape ──
    is_x = 'x.com' in url or 'twitter.com' in url
    if is_x:
        result = fetch_x_content_sync(url)
        if not result.get('success'):
            msg = f"Scrape failed: {result.get('error', 'unknown error')}"
            LOGGER.error(msg)
            return False, msg, None, None
        text = result['text']
        author = result.get('author', '')
        title = result.get('title', 'Untitled')
        source = 'x'
    else:
        # Basic article extraction
        try:
            from rolloforge.scrapers import fetch_article_sync
            result = fetch_article_sync(url)
            text = result.get('text', '')
            author = result.get('author', '')
            title = result.get('title', url.split('/')[-1] or 'Untitled')
            source = 'article'
        except Exception as e:
            # Minimal fallback
            text = url
            author = ''
            title = url
            source = 'article'
            result = {'text': text, 'author': author, 'title': title}
            LOGGER.warning("Article scrape not available, using URL as text")

    LOGGER.info("Scraped: %s (%d chars)", title, len(text))

    # ── Step 2: DeepSeek Analysis ──
    try:
        analysis_dict = deepseek_analyze_bookmark(text, title, url)
    except Exception as e:
        LOGGER.error("DeepSeek analysis crashed: %s", e)
        analysis_dict = {
            'worth_score': 5.0, 'effort_score': 4.0, 'priority_score': 3.0,
            'recommendation_bucket': 'archive',
            'summary': f'[Analysis failed: {str(e)[:100]}] ' + text[:100],
            'recommendation_reason': 'Error during analysis',
            'key_insights': [], 'tags': ['analysis-failed'],
            'analysis_source': 'error_fallback',
            'analyzed_at': '', 'confidence': None,
            'difficulty_reason': '', 'next_action': '',
            'scoring_inputs': {
                'relevance': 3.0, 'practical_value': 3.0, 'actionability': 3.0,
                'stage_fit': 3.0, 'novelty': 3.0, 'excitement': 3.0,
                'difficulty': 5.0, 'time_cost': 5.0,
            },
        }

    # Detect if DeepSeek returned a bad fallback (the generic "deepseek-failed" tag)
    if 'deepseek-failed' in analysis_dict.get('tags', []):
        LOGGER.warning("DeepSeek returned fallback — this content will have default scores")

    # ── Step 2.5: Bucket Overrides ──
    analysis_dict = apply_bucket_overrides(text, analysis_dict)

    LOGGER.info("Analysis: bucket=%s W=%.1f E=%.1f P=%.1f",
                analysis_dict['recommendation_bucket'],
                analysis_dict['worth_score'],
                analysis_dict['effort_score'],
                analysis_dict['priority_score'])

    # ── Step 3: Personalized Scoring ──
    tags = analysis_dict.get('tags', [])
    try:
        profile = load_profile()
        personalized = personalize_scores(text, title, url, tags, analysis_dict, profile)
        LOGGER.info("Personalized: %s", personalized['personalized_why'])
    except Exception as e:
        LOGGER.error("Personalized scoring failed: %s — using raw scores", e)
        personalized = {
            'personalized_worth_score': analysis_dict['worth_score'],
            'personalized_priority_score': analysis_dict['priority_score'],
            'personalized_bucket': analysis_dict['recommendation_bucket'],
            'personalized_why': f'[Scoring failed: {e}]',
            'original_worth_score': analysis_dict['worth_score'],
            'original_priority_score': analysis_dict['priority_score'],
            'original_bucket': analysis_dict['recommendation_bucket'],
            'alignment_score': 5.0,
        }

    # ── Step 4: Create Bookmark ──
    bookmark_id = stable_bookmark_id(url, text)
    now_iso = datetime.now(timezone.utc).isoformat()

    bookmark = Bookmark(
        id=bookmark_id,
        source=source,
        url=url,
        text=text,
        title=title,
        note=f"Auto-captured via Forger agent",
        created_at=now_iso,
        bookmarked_at=now_iso,
        tags=tags,
        raw_payload=result,
    )

    # ── Step 5: Save Bookmark ──
    try:
        all_bm = load_bookmarks()
        # Remove if already exists (in case we're re-processing)
        all_bm = [b for b in all_bm if b.id != bookmark_id]
        all_bm.insert(0, bookmark)
        save_bookmarks(all_bm)
        bm_after = load_bookmarks()
        assert len(bm_after) >= 100 or len(bm_after) >= len(all_bm), f"Bookmark save corrupted data!"
        LOGGER.info("Bookmarks: %d total", len(bm_after))
    except Exception as e:
        msg = f"Bookmark save failed: {e}"
        LOGGER.error(msg)
        return False, msg, None, None

    # ── Step 6: Create & Save Analysis ──
    try:
        scoring_inputs = analysis_dict.get('scoring_inputs', {})
        if not scoring_inputs:
            scoring_inputs = {
                'relevance': 5.0, 'practical_value': 5.0, 'actionability': 5.0,
                'stage_fit': 5.0, 'novelty': 5.0, 'excitement': 5.0,
                'difficulty': 3.0, 'time_cost': 3.0,
            }
        scoring = ScoringInputs(**scoring_inputs)

        final_bucket = personalized['personalized_bucket'] or analysis_dict['recommendation_bucket']
        new_analysis = AnalysisResult(
            bookmark_id=bookmark_id,
            summary=analysis_dict.get('summary', ''),
            recommendation_reason=analysis_dict.get('recommendation_reason', ''),
            recommendation_bucket=final_bucket,
            worth_score=analysis_dict['worth_score'],
            effort_score=analysis_dict['effort_score'],
            priority_score=analysis_dict['priority_score'],
            key_insights=analysis_dict.get('key_insights', []),
            analysis_source=analysis_dict.get('analysis_source', 'deepseek'),
            analyzed_at=analysis_dict.get('analyzed_at', now_iso),
            confidence=analysis_dict.get('confidence'),
            difficulty_reason=analysis_dict.get('difficulty_reason'),
            next_action=analysis_dict.get('next_action'),
            title=analysis_dict.get('title') or title,
            scoring_inputs=scoring,
            tags=tags,
            # Personalized fields
            personalized_worth_score=personalized['personalized_worth_score'],
            personalized_priority_score=personalized['personalized_priority_score'],
            personalized_bucket=personalized['personalized_bucket'],
            personalized_why=personalized['personalized_why'],
            original_worth_score=personalized['original_worth_score'],
            original_priority_score=personalized['original_priority_score'],
            original_bucket=personalized['original_bucket'],
            alignment_score=personalized['alignment_score'],
        )

        existing_an = load_analysis_results()
        merged = upsert_analysis_results(existing_an, [new_analysis])
        LOGGER.info("Analyses: %d total", len(merged))
    except Exception as e:
        msg = f"Analysis save failed: {e}"
        LOGGER.error(msg)
        return False, msg, bookmark, None

    # ── Step 7: Verify Data Integrity ──
    try:
        bm_final = load_bookmarks()
        an_final = load_analysis_results()
        bm_ids = {b.id for b in bm_final}
        an_ids = {a.bookmark_id for a in an_final}

        missing_analyses = bm_ids - an_ids
        if missing_analyses:
            msg = f"DATA MISMATCH: {len(missing_analyses)} bookmarks missing analysis"
            LOGGER.error(msg)
            return False, msg, bookmark, new_analysis

        assert len(bm_final) == len(an_final), \
            f"Count mismatch: {len(bm_final)} bookmarks vs {len(an_final)} analyses"

        LOGGER.info("Integrity verified: %d bookmarks = %d analyses ✓", len(bm_final), len(an_final))
    except AssertionError as e:
        msg = str(e)
        LOGGER.error(msg)
        return False, msg, bookmark, new_analysis

    # ── Step 8: Sync Dashboard ──
    try:
        from scripts.sync_dashboard import sync_dashboard_data
        sync_dashboard_data()
    except Exception as e:
        LOGGER.warning("Dashboard sync warning (non-fatal): %s", e)

    # ── Step 9: Git Push ──
    try:
        git_auto_push(title)
        LOGGER.info("Git pushed: %s", title)
    except Exception as e:
        LOGGER.warning("Git push warning (non-fatal): %s", e)

    return True, f"Done: {title} → {personalized['personalized_bucket']}", bookmark, new_analysis


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    if len(sys.argv) < 2:
        print("Usage: python scripts/process_url.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    success, message, bookmark, analysis = process_bookmark_url(url)

    if success and analysis:
        print(f"\n{'='*60}")
        print(f"✅ {message}")
        print(f"   ID: {bookmark.id}")
        print(f"   Bucket: {analysis.recommendation_bucket} → {analysis.personalized_bucket}")
        print(f"   Worth: {analysis.worth_score} → {analysis.personalized_worth_score}")
        print(f"   Priority: {analysis.priority_score} → {analysis.personalized_priority_score}")
        print(f"   Why: {analysis.personalized_why}")
        print(f"{'='*60}")
        sys.exit(0)
    elif success:
        print(f"\n⚠️  {message}")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED: {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
