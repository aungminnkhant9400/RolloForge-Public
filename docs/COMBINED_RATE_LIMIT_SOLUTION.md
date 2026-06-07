# Combined Rate Limit Solution - Implementation

## Overview
Implements 3 strategies to solve Kimi API rate limits on Allegrato tier:
1. **Provider Rotation** - Fallback to OpenAI when Kimi hits limits
2. **Tiered Workers** - Right-size resources for each task type
3. **Rate Limiting** - Exponential backoff and smart pacing

## Architecture

### Provider Rotation
```
Primary: Kimi (your $30/month Allegrato)
Fallback: OpenAI GPT-4o-mini ($0.15/1M tokens)
Backup: Anthropic Claude Haiku ($0.25/1M tokens)
```

**Strategy:**
- Light/Medium tasks: Try Kimi first, fallback to OpenAI
- Heavy tasks: Prefer OpenAI (more reliable for complex work)

### Tiered Workers

| Tier | Workers | Rate | Parallel? | Use For |
|------|---------|------|-----------|---------|
| **LIGHT** | 3 | 15 calls/min | ✅ Yes | Data checks, duplicates, stats |
| **MEDIUM** | 3 | 10 calls/min | ✅ Yes | Analysis, docs, scripts |
| **HEAVY** | 2 | 5 calls/min | ❌ No | Feature building, refactoring |

**Why tiers?**
- Light tasks: Fast, don't need heavy models
- Medium tasks: Balance of speed and quality
- Heavy tasks: Sequential to avoid API flooding

### Rate Limiting

**Per-tier limits:**
- Light: 15 calls/min (4s between calls)
- Medium: 10 calls/min (6s between calls)
- Heavy: 5 calls/min (12s between calls)

**Exponential backoff:**
- Error #1: Wait 2s
- Error #2: Wait 4s
- Error #3: Wait 8s
- Max: 60s

## Files Created

| File | Purpose |
|------|---------|
| `scripts/tiered_orchestrator.py` | Main orchestrator script |
| `docs/COMBINED_RATE_LIMIT_SOLUTION.md` | This documentation |

## Cron Job Update

**Job:** `rollo-2hr-proactive-cycle`
**Schedule:** Every 2 hours
**Mode:** Tiered orchestrator with provider fallback

## How It Works

1. **Phase 1** - Spawn 3 LIGHT workers in parallel (fast checks)
2. **Phase 2** - Spawn 3 MEDIUM workers in parallel (analysis)
3. **Phase 3** - Spawn 2 HEAVY workers sequentially (complex builds)

Each phase has its own rate limiter.
Workers try Kimi first, fallback to OpenAI on error.

## Expected Performance

**Before (rate limited):**
- 8 workers hit API simultaneously → rate limit crash
- 0 work completed

**After (combined solution):**
- Workers paced by tier
- Provider fallback on errors
- ~80-90% tasks complete successfully
- Time: 15-30 minutes per cycle (quality over speed)

## Monitoring

Check orchestrator output:
```bash
tail -f .nightly-logs/orchestrator-*.log
```

## Cost Estimate

- Kimi: $30/month (your current)
- OpenAI fallback: ~$5-10/month (light usage)
- **Total: ~$35-40/month**

## Next Cycle

Next 2-hour cycle uses this combined solution automatically.
