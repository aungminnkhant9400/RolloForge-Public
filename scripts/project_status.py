#!/usr/bin/env python3
"""
Project Status Dashboard - Unified health view for RolloForge

Aggregates data from multiple sources:
- analysis_results.json - Queue, priority scores, buckets
- stats_summary.json - Aggregate metrics
- GitHub API - PRs, commits, issues
- File timestamps - Stale item detection
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rolloforge.project_dashboard import ProjectDashboard, OutputFormat


def main():
    parser = argparse.ArgumentParser(
        prog="forge-status",
        description="Project Status Dashboard for RolloForge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  forge status                    Show status in console
  forge status --format html      Generate HTML report
  forge status --format md        Generate Markdown report
  forge status --format json      Output JSON data
  forge status --output report.html  Save to file
        """
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["console", "md", "html", "json"],
        default="console",
        help="Output format (default: console)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file (default: stdout for md/html/json)"
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=7,
        help="Days before items are considered stale (default: 7)"
    )
    parser.add_argument(
        "--priority-threshold",
        type=float,
        default=7.0,
        help="Minimum priority score for action items (default: 7.0)"
    )
    parser.add_argument(
        "--github-repo",
        default="aungminnkhant9400/RolloForge",
        help="GitHub repo for activity summary"
    )
    
    args = parser.parse_args()
    
    # Create dashboard instance
    dashboard = ProjectDashboard(
        stale_days=args.stale_days,
        priority_threshold=args.priority_threshold,
        github_repo=args.github_repo
    )
    
    # Generate report
    try:
        output = dashboard.generate(format=OutputFormat(args.format))
        
        if args.output and args.format != "console":
            Path(args.output).write_text(output, encoding="utf-8")
            print(f"✓ Saved {args.format} report to {args.output}")
        else:
            print(output)
        
        return 0
    except Exception as e:
        print(f"Error generating dashboard: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
