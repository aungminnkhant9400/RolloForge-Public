#!/usr/bin/env python3
"""
RolloForge Dashboard Health Check Script

Checks:
- Bookmark count matches analysis count
- Recent git push status
- Data file sizes

Outputs: OK / WARNING / CRITICAL
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Configuration
DATA_DIR = Path("/home/ubuntu/RolloForge/data")
REPO_DIR = Path("/home/ubuntu/RolloForge")
FILE_SIZE_WARN_MB = 5  # Warn if any data file > 5MB
FILE_SIZE_CRIT_MB = 20  # Critical if any data file > 20MB
GIT_PUSH_WARN_HOURS = 24  # Warn if no push in 24 hours
GIT_PUSH_CRIT_HOURS = 72  # Critical if no push in 72 hours

class HealthStatus:
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

def load_json(filepath):
    """Load JSON file, return empty list/dict on error."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        return None

def get_bookmark_count():
    """Get total bookmark count from bookmarks_raw.json."""
    data = load_json(DATA_DIR / "bookmarks_raw.json")
    if data is None:
        return None, "Failed to load bookmarks_raw.json"
    return len(data), None

def get_analysis_count():
    """Get total analysis count from analysis_results.json."""
    data = load_json(DATA_DIR / "analysis_results.json")
    if data is None:
        return None, "Failed to load analysis_results.json"
    return len(data), None

def check_bookmark_analysis_match():
    """Check if bookmark count matches analysis count."""
    bookmark_count, err = get_bookmark_count()
    if err:
        return HealthStatus.CRITICAL, err
    
    analysis_count, err = get_analysis_count()
    if err:
        return HealthStatus.CRITICAL, err
    
    if bookmark_count == analysis_count:
        return HealthStatus.OK, f"{bookmark_count} bookmarks, {analysis_count} analyses"
    elif abs(bookmark_count - analysis_count) <= 5:
        return HealthStatus.WARNING, f"Mismatch: {bookmark_count} bookmarks vs {analysis_count} analyses (diff: {abs(bookmark_count - analysis_count)})"
    else:
        return HealthStatus.CRITICAL, f"Large mismatch: {bookmark_count} bookmarks vs {analysis_count} analyses (diff: {abs(bookmark_count - analysis_count)})"

def get_git_last_push_time():
    """Get timestamp of last push to origin/main."""
    try:
        # Get the last commit that exists on origin/main
        result = subprocess.run(
            ["git", "log", "origin/main", "-1", "--format=%ct"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return None, "Failed to get git log"
        
        timestamp = int(result.stdout.strip())
        push_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return push_time, None
    except Exception as e:
        return None, str(e)

def get_unpushed_commits():
    """Check if there are unpushed commits."""
    try:
        result = subprocess.run(
            ["git", "log", "origin/main..HEAD", "--oneline"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return None, "Failed to check unpushed commits"
        
        commits = result.stdout.strip().split('\n') if result.stdout.strip() else []
        return len(commits), None
    except Exception as e:
        return None, str(e)

def check_git_status():
    """Check recent git push status."""
    last_push, err = get_git_last_push_time()
    if err:
        return HealthStatus.CRITICAL, f"Git check failed: {err}"
    
    unpushed_count, err = get_unpushed_commits()
    if err:
        return HealthStatus.CRITICAL, f"Git check failed: {err}"
    
    now = datetime.now(timezone.utc)
    hours_since_push = (now - last_push).total_seconds() / 3600
    
    messages = []
    status = HealthStatus.OK
    
    # Check time since last push
    if hours_since_push > GIT_PUSH_CRIT_HOURS:
        status = HealthStatus.CRITICAL
        messages.append(f"Last push {hours_since_push:.1f}h ago (>{GIT_PUSH_CRIT_HOURS}h)")
    elif hours_since_push > GIT_PUSH_WARN_HOURS:
        status = HealthStatus.WARNING
        messages.append(f"Last push {hours_since_push:.1f}h ago (>{GIT_PUSH_WARN_HOURS}h)")
    else:
        messages.append(f"Last push {hours_since_push:.1f}h ago")
    
    # Check for unpushed commits
    if unpushed_count > 0:
        status = HealthStatus.WARNING if status == HealthStatus.OK else status
        messages.append(f"{unpushed_count} unpushed commit(s)")
    
    return status, "; ".join(messages)

def check_file_sizes():
    """Check data file sizes."""
    files_to_check = [
        DATA_DIR / "bookmarks_raw.json",
        DATA_DIR / "analysis_results.json",
        DATA_DIR / "seen_bookmarks.json"
    ]
    
    messages = []
    status = HealthStatus.OK
    total_size_mb = 0
    
    for filepath in files_to_check:
        if not filepath.exists():
            messages.append(f"{filepath.name}: MISSING")
            status = HealthStatus.CRITICAL
            continue
        
        size_bytes = filepath.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        total_size_mb += size_mb
        
        if size_mb > FILE_SIZE_CRIT_MB:
            status = HealthStatus.CRITICAL
            messages.append(f"{filepath.name}: {size_mb:.1f}MB (>{FILE_SIZE_CRIT_MB}MB)")
        elif size_mb > FILE_SIZE_WARN_MB:
            if status == HealthStatus.OK:
                status = HealthStatus.WARNING
            messages.append(f"{filepath.name}: {size_mb:.1f}MB (>{FILE_SIZE_WARN_MB}MB)")
        else:
            messages.append(f"{filepath.name}: {size_mb:.1f}MB")
    
    messages.append(f"Total: {total_size_mb:.1f}MB")
    return status, "; ".join(messages)

def main():
    """Run all health checks and output results."""
    print("=" * 60)
    print("RolloForge Dashboard Health Check")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    checks = [
        ("Bookmark/Analysis Count", check_bookmark_analysis_match),
        ("Git Push Status", check_git_status),
        ("Data File Sizes", check_file_sizes),
    ]
    
    overall_status = HealthStatus.OK
    results = []
    
    for check_name, check_func in checks:
        status, message = check_func()
        results.append((check_name, status, message))
        
        # Aggregate status (worst wins)
        if status == HealthStatus.CRITICAL:
            overall_status = HealthStatus.CRITICAL
        elif status == HealthStatus.WARNING and overall_status == HealthStatus.OK:
            overall_status = HealthStatus.WARNING
    
    # Print individual results
    for check_name, status, message in results:
        status_emoji = {
            HealthStatus.OK: "✓",
            HealthStatus.WARNING: "⚠",
            HealthStatus.CRITICAL: "✗"
        }.get(status, "?")
        print(f"{status_emoji} {check_name}: {status}")
        print(f"  └─ {message}")
        print()
    
    # Print overall status
    print("-" * 60)
    status_emoji = {
        HealthStatus.OK: "✓",
        HealthStatus.WARNING: "⚠",
        HealthStatus.CRITICAL: "✗"
    }.get(overall_status, "?")
    print(f"OVERALL STATUS: {status_emoji} {overall_status}")
    print("=" * 60)
    
    # Exit with appropriate code
    exit_codes = {
        HealthStatus.OK: 0,
        HealthStatus.WARNING: 1,
        HealthStatus.CRITICAL: 2
    }
    return exit_codes.get(overall_status, 2)

if __name__ == "__main__":
    sys.exit(main())
