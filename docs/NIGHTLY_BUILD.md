# Nightly Build System Documentation

## Overview

The RolloForge Nightly Build is an autonomous code shipping workflow that runs overnight to:

1. **Check System Health** - Detect data inconsistencies, duplicates, missing analyses
2. **Apply Safe Auto-Fixes** - Clean data, fix duplicates, create placeholder analyses
3. **Create Pull Requests** - Open PRs for Rollo's review (never pushes to main)
4. **Generate Reports** - Morning summary of what happened

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NIGHTLY BUILD FLOW                       │
├─────────────────────────────────────────────────────────────┤
│  1. BACKUP → Create timestamped backup of all data          │
│  2. HEALTH → Run comprehensive health checks                │
│  3. DETECT → Find improvement opportunities                 │
│  4. FIX    → Apply safe auto-fixes                          │
│  5. PR     → Create branches and open PRs                   │
│  6. REPORT → Generate morning report                        │
└─────────────────────────────────────────────────────────────┘
```

## Safety First

### Core Principles
- ✅ **Never push to main directly** - All changes go through PRs
- ✅ **Always backup first** - Full data backup before any changes
- ✅ **Auto-fixes only** - Code changes require human review
- ✅ **Fully reversible** - Rollback to any previous state

### Backup System
```bash
# Backups stored in: /home/ubuntu/RolloForge/.nightly-backups/
# Each backup includes:
#   - bookmarks_raw.json
#   - analysis_results.json
#   - seen_bookmarks.json
#   - manifest.json (timestamp, git SHA)

# List backups
./scripts/nightly-build.py --list-backups

# Rollback to specific backup
./scripts/nightly-build.py --rollback 20260331_020000
```

## Components

### 1. nightly-build.py
Main orchestration script with classes:

- **SafetyManager** - Backup/rollback management
- **HealthChecker** - Comprehensive health checks
- **ImprovementDetector** - Find improvement opportunities
- **GitManager** - Branch creation, commits, PRs
- **ReportGenerator** - Morning report generation
- **NightlyBuild** - Main orchestrator

### 2. nightly-cron.sh
Cron wrapper that handles:
- Locking (prevents concurrent runs)
- Environment setup
- Error notifications
- Logging

### 3. Health Checks

| Component | Description | Auto-Fixable |
|-----------|-------------|--------------|
| Bookmark/Analysis Sync | Counts match | Yes |
| Data File Integrity | Valid JSON | No |
| Git Status | Clean working dir | No |
| Duplicate Bookmarks | URL duplicates | Yes |
| Missing Analyses | Unanalyzed bookmarks | Yes |
| File Sizes | Data file bloat | No |
| Recent Activity | Bookmark velocity | No |

## Usage

### Manual Execution

```bash
cd /home/ubuntu/RolloForge

# Full build with auto-fixes
./scripts/nightly-build.py

# Dry run (see what would happen)
./scripts/nightly-build.py --dry-run

# Health checks only
./scripts/nightly-build.py --skip-auto-fix

# Generate report from last run
./scripts/nightly-build.py --report-only

# List and manage backups
./scripts/nightly-build.py --list-backups
./scripts/nightly-build.py --rollback BACKUP_ID
```

### Cron Setup

```bash
# Edit crontab
crontab -e

# Add nightly build at 2 AM
0 2 * * * /home/ubuntu/RolloForge/scripts/nightly-cron.sh

# Add morning report at 8 AM
0 8 * * * /home/ubuntu/RolloForge/scripts/send-morning-report.sh
```

### Configuration

Copy example config and customize:

```bash
cp scripts/nightly-config.example scripts/.nightly-config
# Edit scripts/.nightly-config with your settings
```

Configuration options:
- `GITHUB_TOKEN` - For PR creation
- `TELEGRAM_BOT_TOKEN` - For notifications
- `DRY_RUN` - Test mode
- `SKIP_AUTO_FIX` - Health checks only
- `BACKUP_RETENTION_DAYS` - Cleanup old backups

## Reports

Reports are generated in multiple formats:

```
reports/
├── nightly-report-20260331.txt   # Human-readable
├── nightly-report-20260331.html  # Formatted for viewing
└── nightly-report-20260331.json  # Machine-readable
```

### Report Contents
- Health check summary (✅/⚠️/❌)
- Improvements identified
- Auto-fixes applied
- PRs created with links
- Errors encountered
- Overall status

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Failed (critical error) |
| 2 | Partial (warnings, some issues) |

## Integration with Existing Systems

### Heartbeat Integration
The nightly build is integrated into `HEARTBEAT.md`:
- Runs at 2 AM automatically
- Results available for morning review
- Part of proactive workflow

### Git Workflow Integration
- Uses existing `git-helper.sh` patterns
- Creates descriptive branch names: `auto-fix/remove-duplicate-bookmarks`
- PRs include full context and description

### RolloForge Data Integration
- Reads/writes `bookmarks_raw.json`
- Reads/writes `analysis_results.json`
- Uses existing storage.py for consistency

## Troubleshooting

### Build Fails
```bash
# Check logs
tail -50 /home/ubuntu/RolloForge/.nightly-logs/cron-wrapper.log

# Check specific build log
ls -la /home/ubuntu/RolloForge/.nightly-logs/

# Rollback if needed
./scripts/nightly-build.py --list-backups
./scripts/nightly-build.py --rollback BACKUP_ID
```

### PR Creation Fails
- Ensure `gh` CLI is installed and authenticated
- Check `GITHUB_TOKEN` has PR creation permissions
- Verify remote is set correctly

### Notifications Not Working
- Check Telegram bot token and chat ID
- Ensure `telegram-send` is installed or use webhook
- Review notification settings in config

## Development

### Adding New Health Checks

Edit `HealthChecker` class in `nightly-build.py`:

```python
def _check_my_new_check(self):
    """Description of check"""
    try:
        # Check logic
        if problem:
            self.checks.append(HealthStatus(
                component="My New Check",
                status="WARNING",
                message="Description of issue",
            ))
    except Exception as e:
        self.checks.append(HealthStatus(...))
```

### Adding New Auto-Fixes

Edit `ImprovementDetector` class:

```python
def _detect_my_fix(self):
    """Detect if fix is needed"""
    check = next((c for c in self.health_checks if c.component == "..."), None)
    if check and check.status == "WARNING":
        self.improvements.append(Improvement(
            category="data_quality",
            priority=7,
            title="Fix My Issue",
            description="What needs fixing",
            action_type="auto_fix",
            auto_fix_func=self._fix_my_issue,
        ))

def _fix_my_issue(self) -> dict:
    """Apply the fix"""
    # Fix logic here
    return {"fixed": count}
```

## Security Considerations

1. **Backups contain sensitive data** - Protect `.nightly-backups/` directory
2. **GitHub tokens** - Use fine-grained tokens with minimal permissions
3. **Telegram tokens** - Don't commit to version control
4. **Lock files** - Clean up stale locks manually if needed

## Future Enhancements

- [ ] Webhook notifications (Discord, Slack)
- [ ] Automated test running before PR creation
- [ ] Smart duplicate merging (preserve best analysis)
- [ ] Trend analysis (bookmark velocity, topic drift)
- [ ] Integration with GPU server monitoring
- [ ] Auto-deployment on PR merge

---

**Last Updated:** 2026-03-31
**Version:** 1.0.0
