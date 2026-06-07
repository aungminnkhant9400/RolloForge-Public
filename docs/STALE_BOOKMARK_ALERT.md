# Stale Bookmark Alert System

A proactive automation script that identifies high-priority bookmarks in RolloForge that haven't been acted on within a specified timeframe. Helps prevent "bookmark and forget" syndrome.

## What It Does

- Scans bookmarks in specified buckets (default: `test_this_week`)
- Identifies items that are older than a threshold (default: 7 days)
- Filters by priority score (default: ≥5.0)
- Generates alerts with actionable recommendations
- Optionally sends alerts via Telegram
- Can auto-archive very stale items (≥30 days)

## Usage

### Standalone Script

```bash
# Basic check (default: 7 days, test_this_week bucket)
python scripts/stale_bookmark_alert.py

# Check different buckets
python scripts/stale_bookmark_alert.py --bucket test_this_week build_later

# Adjust stale threshold
python scripts/stale_bookmark_alert.py --days 14

# Only high-priority items
python scripts/stale_bookmark_alert.py --priority-threshold 7.0

# Send Telegram alert
python scripts/stale_bookmark_alert.py --send-telegram

# Dry-run auto-archive
python scripts/stale_bookmark_alert.py --auto-archive --dry-run

# Actually auto-archive very stale items
python scripts/stale_bookmark_alert.py --auto-archive

# JSON output for automation
python scripts/stale_bookmark_alert.py --json-output --quiet
```

### Via Forge CLI

```bash
# Basic check
forge stale

# With options
forge stale --days 14 --bucket build_later --priority-threshold 6.0

# Send Telegram alert
forge stale --send-telegram

# Dry-run auto-archive
forge stale --auto-archive --dry-run
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No stale bookmarks found |
| 1 | Stale bookmarks found (or Telegram send failed with `--send-telegram`) |
| 2 | Configuration or runtime error |

## Configuration

Telegram alerts require environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

Or create `config/telegram.conf`:

```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Sample Output

```
============================================================
📚 STALE BOOKMARK ALERT
============================================================
Found 12 bookmark(s) stale for ≥7 days
Buckets checked: test_this_week
Priority threshold: ≥5.0
Generated: 2026-03-31 08:19 UTC


📁 TEST_THIS_WEEK (12 items)
------------------------------------------------------------

1. OpenClaw 2026.3.23
   🔗 https://x.com/openclaw/status/2036293335007264807?s=46
   ⭐ Priority: 9.2 | Worth: 9.5
   📅 Stale for: 7 days (bookmarked: 2026-03-24)
   🏷️ Tags: openclaw, release-notes
   📝 OpenClaw 2026.3.23 release with DeepSeek provider plugin...

============================================================
💡 RECOMMENDATIONS
============================================================
• You have 12 'test_this_week' item(s) that are stale.
  Consider either testing them or moving to 'build_later'.
```

## Automation Ideas

### Cron Job (Daily Check)

```bash
# Add to crontab
echo "0 9 * * * cd /home/ubuntu/RolloForge && python3 scripts/stale_bookmark_alert.py --send-telegram" | crontab -
```

### Nightly Build Integration

Add to `scripts/nightly-build.py` or `scripts/nightly-cron.sh`:

```bash
# Check for stale bookmarks
python3 scripts/stale_bookmark_alert.py --json-output > reports/stale_check.json
```

### Heartbeat Check

Use during OpenClaw heartbeat to proactively alert on stale items.

## Testing

```bash
# Run unit tests
cd /home/ubuntu/RolloForge
source .venv/bin/activate
pytest tests/test_stale_bookmark_alert.py -v
```

## How It Works

1. **Load Data**: Reads `bookmarks_raw.json` and `analysis_results.json`
2. **Calculate Staleness**: Compares `bookmarked_at` date against threshold
3. **Filter**: Only includes items in specified buckets with priority ≥ threshold
4. **Sort**: Results sorted by priority (highest first), then days stale (oldest first)
5. **Report**: Generates human-readable or JSON output
6. **Alert**: Optionally sends Telegram notification
7. **Archive**: Optionally moves very stale items to `archive` bucket

## Future Enhancements

- [ ] Tag-based filtering (e.g., only stale items with "openclaw" tag)
- [ ] Integration with calendar for "schedule to review" functionality
- [ ] Machine learning to predict which stale bookmarks are most important to revisit
- [ ] Slack/Discord webhook support
