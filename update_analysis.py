import json
from datetime import datetime, timezone

# Load existing analysis
with open('data/analysis_results.json', 'r') as f:
    results = json.load(f)

# Find and update the bookmark
for r in results:
    if r['bookmark_id'] == 'bookmark_1113ab5a3462':
        r['summary'] = "Multi-agent AI R&D department setup using OpenClaw. 5 different AI models meet twice daily to autonomously discuss and analyze business operations."
        r['recommendation_reason'] = "Directly relevant to your multi-agent goals. Demonstrates production-ready autonomous AI team pattern with scheduled collaboration."
        r['key_insights'] = [
            "5 AI models collaborate autonomously",
            "Scheduled meetings (twice daily) for consistency",
            "Business-focused R&D automation pattern",
            "Uses OpenClaw as orchestration layer",
            "Real production use case (not theoretical)"
        ]
        r['scoring_inputs'] = {
            'relevance': 9.0,
            'practical_value': 8.0,
            'actionability': 7.0,
            'stage_fit': 8.0,
            'novelty': 8.0,
            'excitement': 9.0,
            'difficulty': 6.0,
            'time_cost': 5.0
        }
        r['worth_score'] = 8.5
        r['effort_score'] = 5.5
        r['priority_score'] = 8.2
        r['recommendation_bucket'] = 'test_this_week'
        r['analysis_source'] = 'garfis_manual'
        r['analyzed_at'] = datetime.now(timezone.utc).isoformat()
        print(f"Updated: {r['bookmark_id']}")
        break

# Save back
with open('data/analysis_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("Analysis updated!")
