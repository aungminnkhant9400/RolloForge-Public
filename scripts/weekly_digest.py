#!/usr/bin/env python3
"""
Weekly Digest Generator for RolloForge

Generates comprehensive weekly reports of bookmarks with analysis,
trends, and actionable insights.

Usage:
    python weekly_digest.py                    # Generate for last 7 days
    python weekly_digest.py --days 14          # Generate for last 14 days
    python weekly_digest.py --output html      # Output format: html, md, or both
    python weekly_digest.py --save             # Save to reports directory
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jinja2 import Environment, FileSystemLoader

from config.settings import REPORTS_DIR, TEMPLATES_DIR
from rolloforge.digest import generate_weekly_digest, WeeklyDigest


def render_html_digest(digest: WeeklyDigest) -> str:
    """Render digest as HTML."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = env.get_template("digest.html.j2")
    
    # Format dates for display
    week_start_str = digest.week_start.strftime("%b %d")
    week_end_str = digest.week_end.strftime("%b %d, %Y")
    week_range = f"{week_start_str} - {week_end_str}"
    
    return template.render(
        week_range=week_range,
        generated_at=digest.generated_at.strftime("%B %d, %Y at %H:%M"),
        stats=digest.stats,
        test_this_week=digest.test_this_week,
        build_later=digest.build_later,
        archive=digest.archive,
        trends=digest.trends,
        insights=digest.insights,
    )


def render_markdown_digest(digest: WeeklyDigest) -> str:
    """Render digest as Markdown."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = env.get_template("digest.md.j2")
    
    # Format dates for display
    week_start_str = digest.week_start.strftime("%b %d")
    week_end_str = digest.week_end.strftime("%b %d, %Y")
    week_range = f"{week_start_str} - {week_end_str}"
    
    return template.render(
        week_range=week_range,
        generated_at=digest.generated_at.strftime("%B %d, %Y at %H:%M"),
        stats=digest.stats,
        test_this_week=digest.test_this_week,
        build_later=digest.build_later,
        archive=digest.archive,
        trends=digest.trends,
        insights=digest.insights,
    )


def save_digest(html_content: str | None, md_content: str | None, digest: WeeklyDigest) -> dict[str, Path]:
    """Save digest to reports directory."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create filename based on week range
    week_start_str = digest.week_start.strftime("%Y%m%d")
    week_end_str = digest.week_end.strftime("%Y%m%d")
    base_name = f"weekly_digest_{week_start_str}_{week_end_str}"
    
    saved_paths = {}
    
    if html_content:
        html_path = REPORTS_DIR / f"{base_name}.html"
        html_path.write_text(html_content, encoding="utf-8")
        saved_paths['html'] = html_path
        print(f"✓ Saved HTML: {html_path}")
    
    if md_content:
        md_path = REPORTS_DIR / f"{base_name}.md"
        md_path.write_text(md_content, encoding="utf-8")
        saved_paths['md'] = md_path
        print(f"✓ Saved Markdown: {md_path}")
    
    return saved_paths


def print_console_summary(digest: WeeklyDigest) -> None:
    """Print a brief summary to console."""
    week_start_str = digest.week_start.strftime("%b %d")
    week_end_str = digest.week_end.strftime("%b %d")
    
    print("\n" + "=" * 60)
    print(f"📚 ROLLOFORGE WEEKLY DIGEST")
    print(f"   {week_start_str} - {week_end_str}")
    print("=" * 60)
    
    # Stats
    print(f"\n📊 SUMMARY")
    print(f"   New bookmarks:     {digest.stats.total_new}")
    print(f"   Analyzed:          {digest.stats.analyzed}")
    print(f"   ⚡ Test this week: {digest.stats.test_this_week}")
    print(f"   📚 Build later:    {digest.stats.build_later}")
    print(f"   📁 Archive:        {digest.stats.archive}")
    
    if digest.stats.avg_worth_score > 0:
        print(f"\n   Avg worth score:   {digest.stats.avg_worth_score:.1f}/10")
        print(f"   Avg priority:      {digest.stats.avg_priority_score:.1f}/10")
    
    # Insights
    if digest.insights:
        print(f"\n💡 INSIGHTS")
        for insight in digest.insights[:5]:
            print(f"   {insight}")
    
    # Top items
    if digest.test_this_week:
        print(f"\n⚡ TOP PRIORITY ITEMS")
        for i, item in enumerate(digest.test_this_week[:3], 1):
            title = item.bookmark.title or item.bookmark.text[:50] + "..."
            print(f"   {i}. {title}")
            print(f"      Worth: {item.analysis.worth_score:.1f} | Priority: {item.analysis.priority_score:.1f}")
            if item.action_items:
                print(f"      → {item.action_items[0]}")
    
    # Trends
    if digest.trends.get('quality_trend'):
        trend = digest.trends['quality_trend']
        delta = digest.trends.get('quality_delta', 0)
        print(f"\n📈 TRENDS")
        print(f"   Quality trend: {'📈 Up' if trend == 'up' else '📉 Down' if trend == 'down' else '➡️ Stable'}", end="")
        if delta != 0:
            print(f" ({delta:+.2f})")
        else:
            print()
    
    print("\n" + "=" * 60)


def main(parsed_args=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate weekly digest of RolloForge bookmarks"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to include (default: 7)"
    )
    parser.add_argument(
        "--output",
        choices=["html", "md", "markdown", "both"],
        default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save to reports directory"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Don't print console summary"
    )
    
    args = parsed_args if parsed_args is not None else parser.parse_args()
    
    try:
        # Generate digest
        print(f"Generating weekly digest (last {args.days} days)...")
        digest = generate_weekly_digest(days=args.days)
        
        # Render outputs
        html_content = None
        md_content = None
        
        if args.output in ("html", "both"):
            html_content = render_html_digest(digest)
        
        if args.output in ("md", "markdown", "both"):
            md_content = render_markdown_digest(digest)
        
        # Save if requested
        if args.save:
            saved = save_digest(html_content, md_content, digest)
            print(f"\nSaved {len(saved)} file(s) to {REPORTS_DIR}")
        
        # Print console summary unless quiet
        if not args.quiet:
            print_console_summary(digest)
        
        # Output to stdout if not saving
        if not args.save:
            if html_content and args.output == "html":
                print(html_content)
            elif md_content and args.output in ("md", "markdown"):
                print(md_content)
        
        return 0
        
    except Exception as e:
        print(f"Error generating digest: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
