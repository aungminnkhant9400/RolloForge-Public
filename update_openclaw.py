import json
from datetime import datetime, timezone

# Load existing analysis
with open('data/analysis_results.json', 'r') as f:
    results = json.load(f)

# Find and update the OpenClaw bookmark
for r in results:
    if r['bookmark_id'] == 'bookmark_27b42cdf3981':
        r['summary'] = "OpenClaw 2026.3.23 release with DeepSeek provider plugin, Qwen pay-as-you-go, OpenRouter auto pricing, Chrome MCP improvements, and Web UI fixes."
        r['recommendation_reason'] = "Critical update - DeepSeek plugin may fix tool parameter bugs you experienced. Includes new model providers and automation improvements."
        r['key_insights'] = [
            "DeepSeek provider plugin - direct access without workarounds",
            "Qwen pay-as-you-go - cheap Alibaba models",
            "OpenRouter auto pricing - better cost control",
            "Chrome MCP tab waiting - browser automation fixes",
            "Discord/Slack/Matrix + Web UI bug fixes"
        ]
        r['scoring_inputs'] = {
            'relevance': 10.0,
            'practical_value': 9.0,
            'actionability': 10.0,
            'stage_fit': 9.0,
            'novelty': 7.0,
            'excitement': 8.0,
            'difficulty': 2.0,
            'time_cost': 1.0
        }
        r['worth_score'] = 9.5
        r['effort_score'] = 1.5
        r['priority_score'] = 9.2
        r['recommendation_bucket'] = 'test_this_week'
        r['analysis_source'] = 'garfis_manual'
        r['analyzed_at'] = datetime.now(timezone.utc).isoformat()
        print(f"Updated: {r['bookmark_id']}")
        break

# Save back
with open('data/analysis_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("Analysis updated!")
