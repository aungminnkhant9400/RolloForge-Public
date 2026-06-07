#!/usr/bin/env python3
"""Process X bookmark with DeepSeek analysis."""
import json
import sys
sys.path.insert(0, '/home/ubuntu/RolloForge')

from datetime import datetime, timezone
from rolloforge.storage import load_bookmarks, save_bookmarks, load_analysis_results
from rolloforge.deepseek_analysis import analyze_with_deepseek
from rolloforge.telegram_ingest import parse_frictionless_url, bookmark_from_parsed_message, _generate_title

# Bookmark data
url = "https://x.com/crc_8341/status/2044309177158512951?s=46"
text = """Tsinghua College of AI Professor Alex Lamb is recruiting PhD students in AI research. 

Open to International (non-Chinese citizens) + HK/Taiwan residents

Lamb was the PhD student of Turing Award Winner Yoshua Bengio  
 
Email: Lambalex@tsinghua.edu.cn"""
author = "crc_8341"
title = "Tsinghua College of AI Professor Alex Lamb recruiting PhD students"

# Create bookmark
parsed = parse_frictionless_url(url)
bookmark = bookmark_from_parsed_message(parsed)
bookmark.text = text
bookmark.title = title
bookmark.author = author
bookmark.source = "x"

# Save bookmark
bookmarks = load_bookmarks()
bookmarks.insert(0, bookmark)
save_bookmarks(bookmarks)
print(f"✅ Saved bookmark: {bookmark.id}")

# DeepSeek analysis
print(f"🤖 Running DeepSeek analysis...")
deepseek_result = analyze_with_deepseek(
    text=text,
    title=title,
    url=url
)

if deepseek_result:
    analysis = {
        "bookmark_id": bookmark.id,
        "summary": deepseek_result.get('summary', 'Analysis pending'),
        "recommendation_reason": deepseek_result.get('reasoning', ''),
        "key_insights": deepseek_result.get('key_insights', []),
        "scoring_inputs": {
            "relevance": deepseek_result.get('relevance', 5.0),
            "practical_value": deepseek_result.get('practical_value', 5.0),
            "actionability": deepseek_result.get('actionability', 5.0),
            "stage_fit": 7.0,
            "novelty": 6.0,
            "excitement": 6.0,
            "difficulty": 5.0,
            "time_cost": 3.0,
        },
        "worth_score": deepseek_result.get('priority_score', 5.0),
        "effort_score": 3.0,
        "priority_score": deepseek_result.get('priority_score', 5.0),
        "recommendation_bucket": deepseek_result.get('bucket', 'archive'),
        "analysis_source": "deepseek",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
    print(f"✅ Analysis complete - Bucket: {analysis['recommendation_bucket']}")
else:
    analysis = {
        "bookmark_id": bookmark.id,
        "summary": "DeepSeek analysis failed",
        "recommendation_reason": "AI analysis failed",
        "key_insights": [],
        "scoring_inputs": {"relevance": 0, "practical_value": 0, "actionability": 0, "stage_fit": 0, "novelty": 0, "excitement": 0, "difficulty": 0, "time_cost": 0},
        "worth_score": 0.0,
        "effort_score": 0.0,
        "priority_score": 0.0,
        "recommendation_bucket": "pending",
        "analysis_source": "failed",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
    print("❌ Analysis failed")

# Save analysis
existing = load_analysis_results()
existing = [a for a in existing if a.bookmark_id != bookmark.id]

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

with open('/home/ubuntu/RolloForge/data/analysis_results.json', 'w') as f:
    json.dump(existing_dicts, f, indent=2)

print(f"✅ Saved analysis to analysis_results.json")
print(json.dumps({"bookmark_id": bookmark.id, "bucket": analysis['recommendation_bucket'], "priority": analysis['priority_score']}, indent=2))
