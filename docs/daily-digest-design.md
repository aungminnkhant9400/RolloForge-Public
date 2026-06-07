# Bookmark Daily Digest System - Design Document

## Overview

A lightweight daily summary system for RolloForge bookmarks that sends morning briefings via Telegram. Complements the existing weekly digest with a more immediate, "what happened today" focus.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Data Layer    │────▶│  Digest Engine   │────▶│  Formatters     │
│                 │     │                  │     │                 │
│ bookmarks_raw   │     │ daily_digest.py  │     │ TelegramDaily   │
│ analysis_results│     │  - Stats calc    │     │ Formatter       │
│                 │     │  - Streak track  │     │  - Morning      │
│                 │     │  - Comparison    │     │  - Summary      │
│                 │     │                  │     │  - Detailed     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Cron Scheduler │────▶│  Sender Script   │────▶│   Telegram      │
│                 │     │                  │     │                 │
│ 0 9 * * *       │     │ send_daily_      │     │ Morning digest  │
│ (9 AM daily)    │     │ digest.py        │     │ delivered       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Key Differences from Weekly Digest

| Feature | Weekly Digest | Daily Digest |
|---------|---------------|--------------|
| **Frequency** | Once per week | Every morning |
| **Focus** | Comprehensive review | "What happened today" |
| **Length** | Multiple messages | Single message (usually) |
| **Format** | Formal report | Conversational briefing |
| **Features** | Trends, deep analysis | Streaks, quick takes |
| **Best for** | Weekend planning | Morning orientation |

## Components

### 1. Core Module: `rolloforge/daily_digest.py`

**Purpose:** Generate daily digest data structures

**Key Classes:**
- `DailyDigest` - Main data container
- `DailyStats` - Aggregated statistics
- `DailyDigestItem` - Bookmark + analysis + quick take
- `StreakInfo` - Streak tracking data

**Key Functions:**
- `generate_daily_digest()` - Main entry point
- `calculate_streak()` - Track consecutive bookmarking days
- `compare_to_yesterday()` - Day-over-day comparison
- `extract_quick_take()` - One-line actionable summary
- `get_greeting()` - Time-appropriate greeting

**Features:**
- Streak calculation (current + longest)
- Yesterday comparison (trend up/down/same)
- Topic extraction
- Time-appropriate greetings

### 2. Sender Script: `scripts/send_daily_digest.py`

**Purpose:** Send formatted digests via Telegram

**Formats:**
1. **Morning** (default) - Friendly briefing with highlights
2. **Summary** - Ultra-concise, one message
3. **Detailed** - Full breakdown, multiple messages

**Environment Variables:**
```bash
TELEGRAM_BOT_TOKEN   # Required
TELEGRAM_CHAT_ID     # Required
TELEGRAM_TOPIC_ID    # Optional (for forum topics)
```

**Usage:**
```bash
# Send today's digest (morning format)
python scripts/send_daily_digest.py

# Dry run to preview
python scripts/send_daily_digest.py --dry-run

# Specific date
python scripts/send_daily_digest.py --date 2026-04-01

# Different format
python scripts/send_daily_digest.py --format summary
python scripts/send_daily_digest.py --format detailed

# Adjust highlight count
python scripts/send_daily_digest.py --highlight 3
```

### 3. Template: `templates/daily_digest.md.j2`

**Purpose:** Markdown version for file export/saving

**Sections:**
- Header with greeting and date
- Streak info
- Statistics table
- Highlighted items with quick takes
- Quick list table (remaining items)
- Topics breakdown
- Quick actions

## Digest Content Structure

### Morning Format (Default)

```
☀️ Good morning!
📅 Thursday, April 2

🔥 5 day streak! Keep it going

📊 Today's Summary
• 8 new bookmarks
• ⚡ 2 high priority
• 📚 3 medium priority

📈 3 more than yesterday

⭐ Highlights
1. ⚡ [Title](url)
   Worth: 8.5 | Priority: 9.0
   👉 Quick action summary

2. 📚 [Title](url)
   👉 Another action item

[View Dashboard]
_Generated at 09:00_
```

### Summary Format

```
📚 Daily Brief | Apr 2
• 8 saved · ⚡ 2 · 📚 3
🔥 5 day streak

1. [First item](url)
2. [Second item](url)
3. [Third item](url)
```

### Detailed Format

Multiple messages:
1. Full statistics + streak
2. High priority items (up to 5)
3. Other items
4. Topics + footer

## Streak System

Tracks consecutive days with at least one bookmark saved.

**Levels:**
- 1 day: "First bookmark of the streak!"
- 2-3 days: "🔥 N day streak"
- 4-6 days: "🔥 N day streak! Keep it going"
- 7-13 days: "🔥 N day streak! You're on fire"
- 14+ days: "🚀 N day streak! Legendary"

**Break conditions:**
- Missing 2 consecutive days breaks streak
- Today OR yesterday counts as active

## Scheduling

### Cron Setup

```bash
# Daily at 9:00 AM
0 9 * * * cd /home/ubuntu/RolloForge && python scripts/send_daily_digest.py --format morning --save

# Alternative: 8:30 AM for early birds
30 8 * * * cd /home/ubuntu/RolloForge && python scripts/send_daily_digest.py
```

### OpenClaw Cron

```bash
# Via OpenClaw's cron system
openclaw cron add --name "daily-digest" \
  --schedule "0 9 * * *" \
  --command "python /home/ubuntu/RolloForge/scripts/send_daily_digest.py --save"
```

## Data Flow

1. **Cron triggers** at scheduled time
2. **Sender script** loads bookmarks and analyses
3. **Daily digest module** filters to today's date
4. **Stats calculated:** counts, averages, streaks, comparisons
5. **Items sorted** by priority score
6. **Formatter** generates Telegram-friendly output
7. **Message(s)** sent via Bot API
8. **Optional:** Save to reports directory

## Error Handling

- Missing credentials → Helpful error message with setup instructions
- No bookmarks today → Still sends streak info + "No new bookmarks today"
- API failures → Retry logic + console error
- Date parsing errors → Clear error message with accepted formats

## Future Enhancements

1. **Web Dashboard Widget** - Embed daily digest on RolloForge web
2. **Email Format** - HTML email version
3. **Smart Scheduling** - Learn user's active hours
4. **Digest Preferences** - User-configurable highlight count, format
5. **Weekend Mode** - Different format for weekends
6. **Digest Archive** - Browse historical daily digests
7. **Weekly Digest Integration** - Daily → Weekly rollup

## Integration Points

- Uses existing `rolloforge.models.Bookmark` and `AnalysisResult`
- Uses existing `rolloforge.storage.load_bookmarks()` and `load_analysis_results()`
- Saves to existing `REPORTS_DIR` for archive
- Compatible with existing Telegram bot infrastructure

## Testing

```bash
# Test without sending
cd /home/ubuntu/RolloForge
python scripts/send_daily_digest.py --dry-run

# Test specific date
python scripts/send_daily_digest.py --date 2026-04-01 --dry-run

# Test all formats
for fmt in morning summary detailed; do
  echo "=== Format: $fmt ==="
  python scripts/send_daily_digest.py --format $fmt --dry-run
done
```
