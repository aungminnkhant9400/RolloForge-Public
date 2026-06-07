"""Hybrid analysis workflow - DeepSeek AI + Garfis review.

DeepSeek analyzes instantly, Garfis reviews later if needed.
"""
import json
import os
from datetime import datetime, timezone
from rolloforge.scrapers import fetch_x_content_sync
from rolloforge.telegram_ingest import parse_frictionless_url, bookmark_from_parsed_message, _generate_title
from rolloforge.storage import load_bookmarks, save_bookmarks, load_analysis_results
from rolloforge.deepseek_analysis import analyze_with_deepseek


def save_and_analyze_bookmark(url: str, garfis_review: dict = None) -> dict:
    """
    Save bookmark with DeepSeek AI analysis (instant) + optional Garfis review.
    
    Args:
        url: The URL to bookmark
        garfis_review: Optional manual override from Garfis
    
    Returns:
        dict with bookmark and analysis info
    """
    # Scrape content
    scraped = fetch_x_content_sync(url)
    
    # Create message for parsing
    message = url
    if scraped['success'] and scraped['text']:
        message = f"{url}\n\n{scraped['text'][:500]}"
    
    # Parse and create bookmark
    parsed = parse_frictionless_url(message)
    bookmark = bookmark_from_parsed_message(parsed)
    
    # Override title if scraped
    if scraped['success']:
        bookmark.text = scraped['text']
        bookmark.title = scraped.get('title') or _generate_title(scraped['text'])
        bookmark.author = scraped.get('author')
    
    # Save bookmark
    bookmarks = load_bookmarks()
    bookmarks.insert(0, bookmark)
    save_bookmarks(bookmarks)
    
    # Get DeepSeek analysis (instant)
    print(f"🤖 DeepSeek analyzing: {bookmark.title[:50]}...")
    deepseek_result = analyze_with_deepseek(
        text=bookmark.text,
        title=bookmark.title,
        url=bookmark.url
    )
    
    if deepseek_result:
        # Use DeepSeek analysis
        analysis = {
            "bookmark_id": bookmark.id,
            "summary": deepseek_result.get('summary', 'Analysis pending'),
            "recommendation_reason": deepseek_result.get('reasoning', ''),
            "key_insights": deepseek_result.get('key_insights', []),
            "scoring_inputs": {
                "relevance": deepseek_result.get('relevance', 5.0),
                "practical_value": deepseek_result.get('practical_value', 5.0),
                "actionability": deepseek_result.get('actionability', 5.0),
                "stage_fit": 7.0,  # Default
                "novelty": 6.0,    # Default
                "excitement": 6.0, # Default
                "difficulty": 5.0, # Default
                "time_cost": 3.0,  # Default
            },
            "worth_score": deepseek_result.get('priority_score', 5.0),
            "effort_score": 3.0,  # Default
            "priority_score": deepseek_result.get('priority_score', 5.0),
            "recommendation_bucket": deepseek_result.get('bucket', 'archive'),
            "analysis_source": "deepseek",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Override title with DeepSeek's polished version
        if deepseek_result.get('title'):
            bookmark.title = deepseek_result['title']
            # Re-save bookmark with better title
            for i, bm in enumerate(bookmarks):
                if bm.id == bookmark.id:
                    bookmarks[i] = bookmark
                    break
            save_bookmarks(bookmarks)
    else:
        # Fallback - waiting for Garfis
        analysis = {
            "bookmark_id": bookmark.id,
            "summary": "[DeepSeek failed - awaiting Garfis review] " + bookmark.text[:100],
            "recommendation_reason": "AI analysis failed, manual review needed",
            "key_insights": ["Bookmark saved", f"Content: {len(bookmark.text)} chars"],
            "scoring_inputs": {
                "relevance": 0, "practical_value": 0, "actionability": 0,
                "stage_fit": 0, "novelty": 0, "excitement": 0,
                "difficulty": 0, "time_cost": 0
            },
            "worth_score": 0.0,
            "effort_score": 0.0,
            "priority_score": 0.0,
            "recommendation_bucket": "pending",
            "analysis_source": "pending_garfis",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
    
    # Apply Garfis review if provided
    if garfis_review:
        analysis['summary'] = garfis_review.get('summary', analysis['summary'])
        analysis['recommendation_reason'] = garfis_review.get('recommendation_reason', analysis['recommendation_reason'])
        analysis['key_insights'] = garfis_review.get('key_insights', analysis['key_insights'])
        analysis['priority_score'] = garfis_review.get('priority_score', analysis['priority_score'])
        analysis['recommendation_bucket'] = garfis_review.get('bucket', analysis['recommendation_bucket'])
        analysis['analysis_source'] = 'deepseek_garfis_reviewed'
        analysis['analyzed_at'] = datetime.now(timezone.utc).isoformat()
    
    # Save analysis
    existing = load_analysis_results()
    existing = [a for a in existing if a.bookmark_id != bookmark.id]
    
    # Convert AnalysisResult objects to dicts if needed
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
    
    with open('data/analysis_results.json', 'w') as f:
        json.dump(existing_dicts, f, indent=2)
    
    return {
        "bookmark_id": bookmark.id,
        "title": bookmark.title,
        "text_preview": bookmark.text[:200],
        "total_bookmarks": len(bookmarks),
        "analysis": analysis,
        "source": analysis['analysis_source']
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
        result = save_and_analyze_bookmark(url)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python manual_analysis.py <url>")
