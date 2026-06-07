"""
Project Dashboard - Core aggregation logic for RolloForge status

Aggregates project health data from multiple sources:
- analysis_results.json - Queue, priority scores, buckets
- stats_summary.json - Aggregate metrics  
- GitHub API - PRs, commits, issues
- File timestamps - Stale item detection
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

# Import local modules
from rolloforge.storage import load_bookmarks, load_analysis_results


class OutputFormat(Enum):
    CONSOLE = "console"
    MARKDOWN = "md"
    HTML = "html"
    JSON = "json"


@dataclass
class StaleItem:
    id: str
    title: str
    bucket: str
    priority_score: float
    days_old: int
    next_action: Optional[str] = None


@dataclass
class PriorityItem:
    id: str
    title: str
    bucket: str
    priority_score: float
    worth_score: float
    effort_score: float
    combined_score: float
    next_action: Optional[str] = None


@dataclass
class GitHubActivity:
    open_prs: int = 0
    recent_commits: int = 0
    open_issues: int = 0
    last_push: Optional[str] = None
    recent_prs: list[dict] = field(default_factory=list)
    recent_commits_list: list[dict] = field(default_factory=list)


@dataclass
class DashboardData:
    generated_at: str
    summary: dict[str, Any]
    test_this_week: list[dict]
    stale_items: list[StaleItem]
    priority_rankings: list[PriorityItem]
    github_activity: GitHubActivity
    action_items: list[dict]
    buckets: dict[str, int]
    stats: dict[str, Any]


class ProjectDashboard:
    """Generate unified project status dashboard."""
    
    DATA_DIR = Path("/home/ubuntu/RolloForge/data")
    TEMPLATES_DIR = Path("/home/ubuntu/RolloForge/templates")
    
    def __init__(
        self,
        stale_days: int = 7,
        priority_threshold: float = 7.0,
        github_repo: str = "aungminnkhant9400/RolloForge"
    ):
        self.stale_days = stale_days
        self.priority_threshold = priority_threshold
        self.github_repo = github_repo
        self.bookmark_map: dict[str, Any] = {}
        
    def generate(self, format: OutputFormat = OutputFormat.CONSOLE) -> str:
        """Generate dashboard in specified format."""
        data = self._aggregate_data()
        
        if format == OutputFormat.CONSOLE:
            return self._render_console(data)
        elif format == OutputFormat.MARKDOWN:
            return self._render_markdown(data)
        elif format == OutputFormat.HTML:
            return self._render_html(data)
        elif format == OutputFormat.JSON:
            return self._render_json(data)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _aggregate_data(self) -> DashboardData:
        """Aggregate data from all sources."""
        # Load data
        analyses = load_analysis_results()
        bookmarks = load_bookmarks()
        self.bookmark_map = {b.id: b for b in bookmarks}  # For title lookup
        self.analysis_map = {a.bookmark_id: a for a in analyses}  # For title lookup
        stats = self._load_stats_summary()
        
        # Calculate derived metrics
        test_this_week = self._get_test_this_week(analyses)
        stale_items = self._find_stale_items(analyses)
        priority_rankings = self._calculate_priority_rankings(analyses)
        github_activity = self._fetch_github_activity()
        action_items = self._extract_action_items(analyses)
        buckets = self._count_by_bucket(analyses)
        
        # Build summary
        summary = {
            "total_bookmarks": stats.get("total_bookmarks", len(analyses)),
            "test_this_week_count": len(test_this_week),
            "stale_count": len(stale_items),
            "high_priority_count": len([p for p in priority_rankings if p.priority_score >= 8]),
            "avg_priority": stats.get("priority", {}).get("average", 0),
            "avg_worth": stats.get("average_worth", 0),
            "open_prs": github_activity.open_prs,
            "recent_commits": github_activity.recent_commits,
            "action_items_count": len(action_items),
        }
        
        return DashboardData(
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            test_this_week=test_this_week,
            stale_items=stale_items,
            priority_rankings=priority_rankings,
            github_activity=github_activity,
            action_items=action_items,
            buckets=buckets,
            stats=stats
        )
    
    def _get_bookmark_title(self, bookmark_id: str) -> str:
        """Get bookmark title from id."""
        # First check if analysis has a title
        if bookmark_id in self.analysis_map:
            analysis = self.analysis_map[bookmark_id]
            if analysis.title:
                return analysis.title
        if bookmark_id in self.bookmark_map:
            bookmark = self.bookmark_map[bookmark_id]
            return bookmark.title or bookmark.text[:80] or bookmark_id
        return bookmark_id

    def _load_stats_summary(self) -> dict:
        """Load stats summary JSON."""
        stats_file = self.DATA_DIR / "stats_summary.json"
        if stats_file.exists():
            with open(stats_file) as f:
                return json.load(f)
        return {}
    
    def _get_test_this_week(self, analyses: list) -> list[dict]:
        """Get all test_this_week items sorted by priority."""
        items = []
        for a in analyses:
            if a.recommendation_bucket == "test_this_week":
                items.append({
                    "id": a.bookmark_id,
                    "title": self._get_bookmark_title(a.bookmark_id)[:80],
                    "priority_score": a.priority_score,
                    "worth_score": a.worth_score,
                    "effort_score": a.effort_score,
                    "analyzed_at": getattr(a, 'analyzed_at', None),
                    "next_action": getattr(a, 'next_action', None),
                })
        
        items.sort(key=lambda x: x["priority_score"], reverse=True)
        return items
    
    def _find_stale_items(self, analyses: list) -> list[StaleItem]:
        """Find stale items (older than stale_days)."""
        stale_items = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.stale_days)
        
        for a in analyses:
            if a.recommendation_bucket != "test_this_week":
                continue
                
            analyzed_at = getattr(a, 'analyzed_at', None)
            if not analyzed_at:
                continue
                
            # Parse timestamp
            try:
                if isinstance(analyzed_at, str):
                    # Handle various ISO formats
                    analyzed_at = analyzed_at.replace('Z', '+00:00')
                    analyzed_dt = datetime.fromisoformat(analyzed_at)
                    if analyzed_dt.tzinfo is None:
                        analyzed_dt = analyzed_dt.replace(tzinfo=timezone.utc)
                else:
                    continue
            except (ValueError, TypeError):
                continue
            
            if analyzed_dt < cutoff:
                days_old = (datetime.now(timezone.utc) - analyzed_dt).days
                stale_items.append(StaleItem(
                    id=a.bookmark_id,
                    title=self._get_bookmark_title(a.bookmark_id)[:80],
                    bucket=a.recommendation_bucket,
                    priority_score=a.priority_score,
                    days_old=days_old,
                    next_action=getattr(a, 'next_action', None)
                ))
        
        stale_items.sort(key=lambda x: x.days_old, reverse=True)
        return stale_items
    
    def _calculate_priority_rankings(self, analyses: list) -> list[PriorityItem]:
        """Calculate priority rankings using worth × priority."""
        rankings = []
        
        for a in analyses:
            if a.recommendation_bucket in ["archive", "ignore"]:
                continue
                
            combined = a.worth_score * a.priority_score / 10  # Normalize to ~10 scale
            
            rankings.append(PriorityItem(
                id=a.bookmark_id,
                title=self._get_bookmark_title(a.bookmark_id)[:80],
                bucket=a.recommendation_bucket,
                priority_score=a.priority_score,
                worth_score=a.worth_score,
                effort_score=a.effort_score,
                combined_score=combined,
                next_action=getattr(a, 'next_action', None)
            ))
        
        rankings.sort(key=lambda x: x.combined_score, reverse=True)
        return rankings[:20]  # Top 20
    
    def _fetch_github_activity(self) -> GitHubActivity:
        """Fetch GitHub activity using gh CLI."""
        activity = GitHubActivity()
        
        try:
            # Check if gh is authenticated
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                timeout=10
            )
            if result.returncode != 0:
                return activity
            
            # Fetch open PRs
            result = subprocess.run(
                ["gh", "pr", "list", "--repo", self.github_repo, 
                 "--state", "open", "--json", "number,title,createdAt,author"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                prs = json.loads(result.stdout)
                activity.open_prs = len(prs)
                activity.recent_prs = prs[:5]  # Top 5
            
            # Fetch recent commits (last 7 days)
            since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            result = subprocess.run(
                ["gh", "api", f"repos/{self.github_repo}/commits", 
                 "-q", ".[:10] | map({sha: .sha[:7], message: .commit.message[:50], date: .commit.committer.date, author: .commit.author.name})"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                try:
                    commits = json.loads(result.stdout)
                    activity.recent_commits = len(commits)
                    activity.recent_commits_list = commits
                except json.JSONDecodeError:
                    pass
            
            # Fetch open issues count
            result = subprocess.run(
                ["gh", "api", f"repos/{self.github_repo}", 
                 "-q", ".open_issues_count"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                try:
                    activity.open_issues = int(result.stdout.strip())
                except ValueError:
                    pass
            
            # Get last push
            result = subprocess.run(
                ["gh", "api", f"repos/{self.github_repo}", 
                 "-q", ".pushed_at"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                activity.last_push = result.stdout.strip().strip('"')
                
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        
        return activity
    
    def _extract_action_items(self, analyses: list) -> list[dict]:
        """Extract items with next_action fields."""
        items = []
        
        for a in analyses:
            next_action = getattr(a, 'next_action', None)
            if next_action and next_action != "None" and next_action.strip():
                items.append({
                    "id": a.bookmark_id,
                    "title": self._get_bookmark_title(a.bookmark_id)[:80],
                    "bucket": a.recommendation_bucket,
                    "priority_score": a.priority_score,
                    "next_action": next_action,
                })
        
        items.sort(key=lambda x: x["priority_score"], reverse=True)
        return items
    
    def _count_by_bucket(self, analyses: list) -> dict[str, int]:
        """Count items by bucket."""
        buckets = {}
        for a in analyses:
            bucket = a.recommendation_bucket
            buckets[bucket] = buckets.get(bucket, 0) + 1
        return buckets
    
    def _render_console(self, data: DashboardData) -> str:
        """Render dashboard as console output."""
        lines = []
        
        # Header
        lines.append("=" * 70)
        lines.append("🔥 ROLLOFORGE PROJECT STATUS".center(70))
        lines.append("=" * 70)
        lines.append(f"Generated: {data.generated_at[:19]}")
        lines.append("")
        
        # Summary
        s = data.summary
        lines.append("📊 SUMMARY")
        lines.append("-" * 40)
        lines.append(f"  Total Bookmarks:     {s['total_bookmarks']}")
        lines.append(f"  Test This Week:      {s['test_this_week_count']}")
        lines.append(f"  Stale Items (>7d):   {s['stale_count']}")
        lines.append(f"  High Priority (8+):  {s['high_priority_count']}")
        lines.append(f"  Avg Priority:        {s['avg_priority']:.1f}/10")
        lines.append(f"  Avg Worth:           {s['avg_worth']:.1f}/10")
        lines.append("")
        
        # Buckets
        lines.append("📁 BUCKETS")
        lines.append("-" * 40)
        for bucket, count in sorted(data.buckets.items(), key=lambda x: -x[1]):
            emoji = {"test_this_week": "⚡", "build_later": "📚", 
                     "archive": "📁", "ignore": "🗑️"}.get(bucket, "📄")
            lines.append(f"  {emoji} {bucket:20} {count:3}")
        lines.append("")
        
        # GitHub Activity
        gh = data.github_activity
        lines.append("🐙 GITHUB ACTIVITY")
        lines.append("-" * 40)
        lines.append(f"  Open PRs:        {gh.open_prs}")
        lines.append(f"  Recent Commits:  {gh.recent_commits} (last 7 days)")
        lines.append(f"  Open Issues:     {gh.open_issues}")
        if gh.last_push:
            lines.append(f"  Last Push:       {gh.last_push[:10]}")
        lines.append("")
        
        # Stale Items
        if data.stale_items:
            lines.append(f"⚠️  STALE ITEMS (> {self.stale_days} days)")
            lines.append("-" * 40)
            for item in data.stale_items[:10]:
                lines.append(f"  🔴 {item.days_old}d | P{item.priority_score:.1f} | {item.title[:50]}")
            if len(data.stale_items) > 10:
                lines.append(f"  ... and {len(data.stale_items) - 10} more")
            lines.append("")
        
        # Top Priority Rankings
        lines.append("🏆 TOP PRIORITY (Worth × Priority)")
        lines.append("-" * 40)
        for i, item in enumerate(data.priority_rankings[:10], 1):
            bucket_emoji = {"test_this_week": "⚡", "build_later": "📚"}.get(item.bucket, "📄")
            lines.append(f"  {i:2}. {bucket_emoji} {item.combined_score:.1f} | {item.title[:45]}")
        lines.append("")
        
        # Action Items
        if data.action_items:
            lines.append("📋 ACTION ITEMS")
            lines.append("-" * 40)
            for item in data.action_items[:5]:
                lines.append(f"  • {item['title'][:40]}")
                lines.append(f"    → {item['next_action'][:50]}")
            lines.append("")
        
        lines.append("=" * 70)
        return "\n".join(lines)
    
    def _render_markdown(self, data: DashboardData) -> str:
        """Render dashboard as Markdown using template."""
        template_path = self.TEMPLATES_DIR / "project_status.md.j2"
        
        # Convert dataclasses to dicts for template
        context = {
            "generated_at": data.generated_at,
            "summary": data.summary,
            "buckets": data.buckets,
            "github": {
                "open_prs": data.github_activity.open_prs,
                "recent_commits": data.github_activity.recent_commits,
                "open_issues": data.github_activity.open_issues,
                "last_push": data.github_activity.last_push,
                "recent_prs": data.github_activity.recent_prs,
                "recent_commits_list": data.github_activity.recent_commits_list,
            },
            "stale_items": [self._dataclass_to_dict(i) for i in data.stale_items],
            "priority_rankings": [self._dataclass_to_dict(i) for i in data.priority_rankings[:15]],
            "action_items": data.action_items,
            "stats": data.stats,
            "stale_days": self.stale_days,
        }
        
        if template_path.exists():
            from jinja2 import Template
            template = Template(template_path.read_text())
            return template.render(**context)
        else:
            # Fallback simple markdown
            return self._generate_simple_markdown(data)
    
    def _render_html(self, data: DashboardData) -> str:
        """Render dashboard as HTML using template."""
        template_path = self.TEMPLATES_DIR / "project_status.html.j2"
        
        context = {
            "generated_at": data.generated_at,
            "summary": data.summary,
            "buckets": data.buckets,
            "github": {
                "open_prs": data.github_activity.open_prs,
                "recent_commits": data.github_activity.recent_commits,
                "open_issues": data.github_activity.open_issues,
                "last_push": data.github_activity.last_push,
                "recent_prs": data.github_activity.recent_prs,
                "recent_commits_list": data.github_activity.recent_commits_list,
            },
            "stale_items": [self._dataclass_to_dict(i) for i in data.stale_items],
            "priority_rankings": [self._dataclass_to_dict(i) for i in data.priority_rankings[:15]],
            "action_items": data.action_items,
            "stats": data.stats,
            "stale_days": self.stale_days,
        }
        
        if template_path.exists():
            from jinja2 import Template
            template = Template(template_path.read_text())
            return template.render(**context)
        else:
            # Fallback simple HTML
            return self._generate_simple_html(data)
    
    def _render_json(self, data: DashboardData) -> str:
        """Render dashboard as JSON."""
        output = {
            "generated_at": data.generated_at,
            "summary": data.summary,
            "buckets": data.buckets,
            "github_activity": {
                "open_prs": data.github_activity.open_prs,
                "recent_commits": data.github_activity.recent_commits,
                "open_issues": data.github_activity.open_issues,
                "last_push": data.github_activity.last_push,
                "recent_prs": data.github_activity.recent_prs,
                "recent_commits_list": data.github_activity.recent_commits_list,
            },
            "stale_items": [self._dataclass_to_dict(i) for i in data.stale_items],
            "priority_rankings": [self._dataclass_to_dict(i) for i in data.priority_rankings],
            "action_items": data.action_items,
        }
        return json.dumps(output, indent=2)
    
    def _generate_simple_markdown(self, data: DashboardData) -> str:
        """Generate simple markdown without template."""
        lines = [
            "# RolloForge Project Status",
            f"",
            f"*Generated: {data.generated_at[:19]}*",
            f"",
            "## Summary",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Bookmarks | {data.summary['total_bookmarks']} |",
            f"| Test This Week | {data.summary['test_this_week_count']} |",
            f"| Stale Items | {data.summary['stale_count']} |",
            f"| Open PRs | {data.summary['open_prs']} |",
            f"| Recent Commits | {data.summary['recent_commits']} |",
            f"",
            "## Buckets",
            f"",
        ]
        
        for bucket, count in sorted(data.buckets.items(), key=lambda x: -x[1]):
            lines.append(f"- **{bucket}**: {count}")
        
        if data.stale_items:
            lines.extend([
                f"",
                f"## ⚠️ Stale Items (> {self.stale_days} days)",
                f"",
            ])
            for item in data.stale_items[:10]:
                lines.append(f"- {item.days_old}d | P{item.priority_score:.1f} | {item.title}")
        
        lines.extend([
            f"",
            "## Top Priority Rankings",
            f"",
        ])
        
        for i, item in enumerate(data.priority_rankings[:10], 1):
            lines.append(f"{i}. **{item.combined_score:.1f}** | {item.bucket} | {item.title}")
        
        return "\n".join(lines)
    
    def _generate_simple_html(self, data: DashboardData) -> str:
        """Generate simple HTML without template."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>RolloForge Status</title>
    <style>
        body {{ font-family: sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }}
        .metric {{ display: inline-block; margin: 10px 20px; padding: 15px; background: #f5f5f5; border-radius: 8px; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #333; }}
        .metric-label {{ color: #666; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f0f0f0; }}
        .stale {{ color: #d32f2f; }}
    </style>
</head>
<body>
    <h1>🔥 RolloForge Project Status</h1>
    <p>Generated: {data.generated_at[:19]}</p>
    
    <div class="metrics">
        <div class="metric">
            <div class="metric-value">{data.summary['total_bookmarks']}</div>
            <div class="metric-label">Bookmarks</div>
        </div>
        <div class="metric">
            <div class="metric-value">{data.summary['test_this_week_count']}</div>
            <div class="metric-label">Test This Week</div>
        </div>
        <div class="metric">
            <div class="metric-value">{data.summary['stale_count']}</div>
            <div class="metric-label">Stale Items</div>
        </div>
        <div class="metric">
            <div class="metric-value">{data.summary['open_prs']}</div>
            <div class="metric-label">Open PRs</div>
        </div>
    </div>
    
    <h2>Priority Rankings</h2>
    <table>
        <tr><th>#</th><th>Score</th><th>Bucket</th><th>Title</th></tr>
        {''.join(f"<tr><td>{i}</td><td>{item.combined_score:.1f}</td><td>{item.bucket}</td><td>{item.title}</td></tr>" for i, item in enumerate(data.priority_rankings[:10], 1))}
    </table>
</body>
</html>"""
    
    def _dataclass_to_dict(self, obj) -> dict:
        """Convert dataclass to dict."""
        return {k: v for k, v in obj.__dict__.items()}
