# DeepSeek LLM Integration for RolloForge

## Setup

1. **Set your API key:**
```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

Or add to `.env` file:
```
DEEPSEEK_API_KEY=your-api-key-here
```

2. **Install package:**
```bash
pip install openai
```

## How It Works

When you paste a URL:
1. Scrape content (Playwright for X, direct for articles)
2. **Send to DeepSeek** with personalized prompt
3. DeepSeek returns: title, summary, insights, bucket, priority
4. Save to database with source: "deepseek"

## Prompt Template

```
You are an AI bookmark analyzer. Analyze this content for a user with this profile:

USER PROFILE:
- Building: OpenClaw multi-agent systems
- Interested in: AI trading, Polymarket prediction markets, stock analysis
- Stage: "building by learning" (hands-on, not theory)
- Effort preference: Quick wins (1-2 hours) to medium projects (few days)

HIGH PRIORITY TOPICS (9-10/10):
- OpenClaw setup & customization
- Multi-agent workflows  
- Polymarket/prediction markets
- AI-driven trading strategies

MEDIUM PRIORITY (6-8/10):
- Agent frameworks
- LLM optimization
- Automation tools

LOW PRIORITY (1-5/10):
- Pure theory without code
- Crypto (unless trading-related)

TRUSTED SOURCES (boost priority):
- Karpathy (+1.5)
- Verified AI builders

CONTENT TO ANALYZE:
[scraped content here]

RESPOND IN JSON:
{
  "title": "Polished title (concise, professional, no dots)",
  "summary": "What it is + why this specific user should care",
  "key_insights": ["3-5 bullet points"],
  "bucket": "test_this_week|build_later|archive|ignore",
  "priority_score": 0-10,
  "relevance": 0-10,
  "practical_value": 0-10,
  "actionability": 0-10,
  "reasoning": "Why you assigned this bucket and score"
}
```

## Example Output

```json
{
  "title": "Autoresearch Guide: Running 100 Experiments Overnight",
  "summary": "Karpathy's autoresearch pattern for any measurable task. Agent modifies code, runs 5-min experiments, keeps improvements. Perfect for user's OpenClaw skills and trading strategies - anything with a numerical score.",
  "key_insights": [
    "Pattern works on any measurable task, not just ML",
    "Apply to OpenClaw skills, trading strategies, predictions",
    "12 experiments/hour, 100 overnight",
    "$25 + single GPU cost",
    "Tobi Lutke: 53% faster Shopify rendering"
  ],
  "bucket": "test_this_week",
  "priority_score": 8.5,
  "relevance": 9.0,
  "practical_value": 9.0,
  "actionability": 9.0,
  "reasoning": "Directly applicable to user's OpenClaw focus and trading background. Implementation-heavy pattern with clear ROI. Karpathy source adds credibility."
}
```

## Cost Estimate

- **Per analysis:** ~$0.003 (3/10 of a cent)
- **50 bookmarks/month:** ~$0.15
- **100 bookmarks/month:** ~$0.30

Very cheap.

## Fallback

If DeepSeek API fails:
1. Retry once
2. If still fails → use heuristic scoring (current system)
3. Mark as "deepseek_fallback" in analysis_source

## Integration

Replace `analyze_bookmark()` in `rolloforge/analysis.py` with DeepSeek call.

Keep manual override option for when you want to adjust scores.