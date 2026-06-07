# Forge CLI Documentation

The Forge CLI is a unified command-line interface for RolloForge that brings together all operations into a single, easy-to-use tool.

## Installation

The CLI is included with RolloForge. To use it from anywhere:

```bash
# From the RolloForge directory
./forge --help

# Or using Python directly
python3 forge.py --help

# Optional: Add to your PATH
ln -s $(pwd)/forge ~/.local/bin/forge
```

## Commands

### `add` - Add a Bookmark

Add a new bookmark from a URL. This runs the full workflow: scrape, analyze, save, and push.

```bash
forge add <url>

# Example
forge add https://x.com/user/status/123456
```

**Output:**
- Bookmark title and metadata
- AI-assigned bucket (test_this_week, build_later, archive)
- Priority score
- Tags extracted from content
- Git push status

---

### `stats` - Dashboard Statistics

Show comprehensive statistics about your bookmarks.

```bash
forge stats
```

**Output:**
- Total bookmark and analysis counts
- Bucket distribution with visual bars
- Average scores (worth, priority, effort)
- Top 10 tags
- 5 most recent bookmarks

---

### `digest` - Generate Weekly Digest

Generate a weekly digest of bookmarks with analysis and insights.

```bash
# Generate digest for last 7 days
forge digest

# Generate for custom period
forge digest --days 14

# Save to reports directory
forge digest --save

# Send via Telegram
forge digest --send-telegram

# Concise output only
forge digest --quiet
```

**Options:**
- `--days N` - Number of days to include (default: 7)
- `--output {html,md,both}` - Output format (default: both)
- `--save` - Save to reports directory
- `--send-telegram` - Send digest via Telegram bot
- `--telegram-format {concise,full,stats_only}` - Telegram message format
- `--quiet` - Don't print console summary

---

### `health` - System Health Check

Check the health of your RolloForge installation.

```bash
# One-time health check
forge health

# Continuous monitoring (refreshes every 30s)
forge health --watch

# Custom refresh interval
forge health --watch --interval 60
```

**Checks:**
1. **Data Consistency** - Bookmark/analysis count parity
2. **Git Repository** - Uncommitted changes, unpushed commits
3. **Data Files** - File sizes and existence
4. **Environment** - Required and optional env vars

**Exit Codes:**
- `0` - All checks passed
- `1` - Warnings present
- `2` - Critical issues found

---

### `search` - Search Bookmarks

Search through all bookmarks with intelligent scoring.

```bash
forge search <query>

# Example
forge search "multi-agent"
forge search "openclaw"

# Limit results
forge search "trading" --limit 10
```

**Search Scoring:**
- Title match: +10 points
- Tag match: +8 points
- Text match: +5 points
- Summary match: +3 points
- Insight match: +2 points

**Output:**
- Ranked results by relevance
- Bucket and priority info
- Match locations

---

### `export` - Export Data

Export bookmarks to various formats.

```bash
# Export to JSON (default)
forge export --format json --output bookmarks.json

# Export to CSV
forge export --format csv --output bookmarks.csv

# Export to Markdown
forge export --format markdown --output bookmarks.md

# Export to stdout
forge export --format json --output -
```

**Formats:**
- `json` - Full data with analysis
- `csv` - Spreadsheet-friendly format
- `markdown` - Human-readable document

---

### `sync` - Sync to Dashboard

Sync data to the web dashboard and optionally push to GitHub.

```bash
# Sync only
forge sync

# Sync and push to GitHub
forge sync --push
```

This updates `web/lib/` and triggers a Vercel deployment.

---

### `config` - Configuration

View or edit RolloForge configuration.

```bash
# Show configuration
forge config

# Edit .env file
forge config --edit
```

**Shows:**
- Project paths
- Environment variables (masked)
- Current bookmark stats

---

### `pipeline` - Run Analysis Pipeline

Run the full analysis pipeline (legacy X bookmark sync + analysis).

```bash
# Full pipeline
forge pipeline

# Skip X sync, analyze existing only
forge pipeline --skip-sync

# Limit number analyzed
forge pipeline --limit 10

# Re-analyze all bookmarks
forge pipeline --force-all
```

---

## Environment Variables

Create a `.env` file in the RolloForge directory:

```bash
# Required
DEEPSEEK_API_KEY=your_key_here

# Optional - for Telegram integration
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional - for X bookmark sync
X_USER_ACCESS_TOKEN=your_token
X_USER_ID=your_user_id
```

---

## Examples

### Daily Workflow

```bash
# Morning: Check stats
forge stats

# Throughout day: Add bookmarks
forge add https://x.com/...

# Evening: Generate digest
forge digest --save --send-telegram

# Weekly: Health check
forge health
```

### Research Workflow

```bash
# Search for relevant bookmarks
forge search "multi-agent"

# Export findings
forge export --format markdown --output research.md

# Sync to dashboard
forge sync --push
```

### Automation

```bash
# Add to crontab for weekly digest
0 9 * * 1 cd /path/to/RolloForge && ./forge digest --send-telegram

# Daily health check
0 */6 * * * cd /path/to/RolloForge && ./forge health
```

---

## Troubleshooting

### Command not found

```bash
# Make sure you're in the RolloForge directory
cd /path/to/RolloForge

# Or use Python directly
python3 forge.py <command>
```

### Import errors

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Git push fails

```bash
# Check git status manually
cd /path/to/RolloForge
git status

# Push manually if needed
git push origin main
```
