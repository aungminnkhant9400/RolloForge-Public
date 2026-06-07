"""
Daily Digest Generation for RolloForge

Generates lightweight daily summaries of bookmarks with:
- Today's new bookmarks
- Quick highlights by priority
- Streak tracking
- Morning briefing format
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from collections import Counter
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Shanghai")

from rolloforge.models import Bookmark, AnalysisResult
from rolloforge.storage import load_bookmarks, load_analysis_results


@dataclass
class DailyStats:
    """Statistics for the day."""
    total_new: int = 0
    analyzed: int = 0
    high_priority: int = 0  # test_this_week
    medium_priority: int = 0  # build_later
    low_priority: int = 0  # archive/ignore
    avg_worth_score: float = 0.0
    avg_priority_score: float = 0.0
    top_source: str | None = None
    top_topics: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class DailyDigestItem:
    """A bookmark with analysis for daily digest."""
    bookmark: Bookmark
    analysis: AnalysisResult
    quick_take: str = ""  # One-line actionable insight


@dataclass
class StreakInfo:
    """Bookmark saving streak information."""
    current_streak: int = 0
    longest_streak: int = 0
    streak_active: bool = False


@dataclass
class DailyDigest:
    """Complete daily digest."""
    date: datetime
    generated_at: datetime
    stats: DailyStats
    highlights: list[DailyDigestItem] = field(default_factory=list)  # Top 3-5 items
    quick_list: list[DailyDigestItem] = field(default_factory=list)  # Rest of items
    streak: StreakInfo = field(default_factory=StreakInfo)
    yesterday_comparison: dict[str, Any] = field(default_factory=dict)
    day_of_week: str = ""
    greeting: str = ""


def parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse ISO datetime string and normalize to local timezone."""
    if not dt_str:
        return None
    try:
        dt_str = dt_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone(LOCAL_TZ).replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


def get_greeting(hour: int | None = None) -> str:
    """Get time-appropriate greeting."""
    if hour is None:
        hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 22:
        return "Good evening"
    else:
        return "Hey there"


def extract_quick_take(analysis: AnalysisResult) -> str:
    """Extract a one-line actionable summary."""
    # Priority: next_action field
    if analysis.next_action and analysis.next_action.lower() not in ['none', 'null', '']:
        return analysis.next_action
    
    # Fallback: first key insight that sounds actionable
    action_words = ['build', 'create', 'implement', 'try', 'test', 'use', 'explore',
                   'consider', 'research', 'learn', 'setup', 'deploy', 'integrate']
    
    for insight in analysis.key_insights[:2]:
        insight_lower = insight.lower()
        if any(word in insight_lower for word in action_words):
            return insight.strip()
    
    # Last resort: truncated summary
    if analysis.summary:
        return analysis.summary[:100] + "..." if len(analysis.summary) > 100 else analysis.summary
    
    return "Worth reviewing"


def calculate_streak(all_bookmarks: list[Bookmark]) -> StreakInfo:
    """Calculate bookmark saving streak."""
    if not all_bookmarks:
        return StreakInfo()
    
    # Get all dates with bookmarks
    dates_with_bookmarks = set()
    for bookmark in all_bookmarks:
        bookmarked_at = parse_datetime(bookmark.bookmarked_at)
        if bookmarked_at:
            dates_with_bookmarks.add(bookmarked_at.date())
    
    if not dates_with_bookmarks:
        return StreakInfo()
    
    sorted_dates = sorted(dates_with_bookmarks, reverse=True)
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Calculate current streak
    current_streak = 0
    streak_active = False
    
    if today in dates_with_bookmarks or yesterday in dates_with_bookmarks:
        streak_active = True
        check_date = today if today in dates_with_bookmarks else yesterday
        
        while check_date in dates_with_bookmarks:
            current_streak += 1
            check_date -= timedelta(days=1)
    
    # Calculate longest streak
    longest_streak = 1
    current_count = 1
    
    sorted_asc = sorted(dates_with_bookmarks)
    for i in range(1, len(sorted_asc)):
        if (sorted_asc[i] - sorted_asc[i-1]).days == 1:
            current_count += 1
            longest_streak = max(longest_streak, current_count)
        else:
            current_count = 1
    
    return StreakInfo(
        current_streak=current_streak,
        longest_streak=longest_streak,
        streak_active=streak_active
    )


def calculate_daily_stats(
    bookmarks: list[Bookmark],
    analyses: list[AnalysisResult]
) -> DailyStats:
    """Calculate statistics for the day."""
    analysis_map = {a.bookmark_id: a for a in analyses}
    
    # Count by priority
    high_priority = 0
    medium_priority = 0
    low_priority = 0
    
    for bookmark in bookmarks:
        if bookmark.id in analysis_map:
            analysis = analysis_map[bookmark.id]
            if analysis.recommendation_bucket == 'test_this_week':
                high_priority += 1
            elif analysis.recommendation_bucket == 'build_later':
                medium_priority += 1
            else:
                low_priority += 1
    
    # Calculate averages
    worth_scores = [a.worth_score for a in analyses]
    priority_scores = [a.priority_score for a in analyses]
    
    # Get top source
    source_counter = Counter(b.source for b in bookmarks if b.source)
    top_source = source_counter.most_common(1)[0][0] if source_counter else None
    
    # Extract topics from analyses
    topic_keywords = {
        'AI Agents': ['agent', 'autonomous', 'multi-agent', 'orchestration'],
        'LLMs': ['llm', 'gpt', 'claude', 'language model', 'fine-tuning'],
        'Coding': ['code', 'programming', 'github', 'developer', 'ide'],
        'Infrastructure': ['docker', 'gpu', 'server', 'deploy', 'kubernetes', 'cloud'],
        'Productivity': ['workflow', 'automation', 'productivity', 'tool'],
        'ML Research': ['training', 'neural', 'deep learning', 'model', 'dataset'],
        'Startup': ['startup', 'founder', 'business', 'revenue', 'growth'],
    }
    
    topic_counter = Counter()
    for analysis in analyses:
        text = f"{analysis.summary} {' '.join(analysis.key_insights)}".lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                topic_counter[topic] += 1
    
    return DailyStats(
        total_new=len(bookmarks),
        analyzed=len(analyses),
        high_priority=high_priority,
        medium_priority=medium_priority,
        low_priority=low_priority,
        avg_worth_score=sum(worth_scores) / len(worth_scores) if worth_scores else 0,
        avg_priority_score=sum(priority_scores) / len(priority_scores) if priority_scores else 0,
        top_source=top_source,
        top_topics=topic_counter.most_common(3)
    )


def compare_to_yesterday(
    today_bookmarks: list[Bookmark],
    today_analyses: list[AnalysisResult],
    all_bookmarks: list[Bookmark],
    all_analyses: list[AnalysisResult]
) -> dict[str, Any]:
    """Compare today's activity to yesterday."""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Get yesterday's bookmarks
    yesterday_bookmarks = []
    yesterday_analyses = []
    analysis_map = {a.bookmark_id: a for a in all_analyses}
    
    for bookmark in all_bookmarks:
        bookmarked_at = parse_datetime(bookmark.bookmarked_at)
        if bookmarked_at and bookmarked_at.date() == yesterday:
            yesterday_bookmarks.append(bookmark)
            if bookmark.id in analysis_map:
                yesterday_analyses.append(analysis_map[bookmark.id])
    
    comparison = {
        'yesterday_count': len(yesterday_bookmarks),
        'today_count': len(today_bookmarks),
        'change': len(today_bookmarks) - len(yesterday_bookmarks),
        'yesterday_high_priority': sum(
            1 for a in yesterday_analyses 
            if a.recommendation_bucket == 'test_this_week'
        ),
        'today_high_priority': sum(
            1 for a in today_analyses 
            if a.recommendation_bucket == 'test_this_week'
        ),
    }
    
    if comparison['change'] > 0:
        comparison['trend'] = '📈'
        comparison['trend_word'] = 'up'
    elif comparison['change'] < 0:
        comparison['trend'] = '📉'
        comparison['trend_word'] = 'down'
    else:
        comparison['trend'] = '➡️'
        comparison['trend_word'] = 'same'
    
    return comparison


def generate_daily_digest(
    date: datetime | None = None,
    highlight_limit: int = 5
) -> DailyDigest:
    """Generate a daily digest of bookmarks."""
    now = datetime.now()
    target_date = date or now
    day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    
    # Load all data
    all_bookmarks = load_bookmarks()
    all_analyses = load_analysis_results()
    analysis_map = {a.bookmark_id: a for a in all_analyses}
    
    # Filter to target day
    today_bookmarks = []
    today_analyses = []
    
    for bookmark in all_bookmarks:
        bookmarked_at = parse_datetime(bookmark.bookmarked_at)
        if bookmarked_at and day_start <= bookmarked_at < day_end:
            today_bookmarks.append(bookmark)
            if bookmark.id in analysis_map:
                today_analyses.append(analysis_map[bookmark.id])
    
    # Calculate stats
    stats = calculate_daily_stats(today_bookmarks, today_analyses)
    
    # Create digest items
    items = []
    for bookmark in today_bookmarks:
        if bookmark.id in analysis_map:
            analysis = analysis_map[bookmark.id]
            quick_take = extract_quick_take(analysis)
            items.append(DailyDigestItem(bookmark, analysis, quick_take))
    
    # Sort by priority score and split into highlights vs quick list
    items.sort(key=lambda x: x.analysis.priority_score, reverse=True)
    highlights = items[:highlight_limit]
    quick_list = items[highlight_limit:]
    
    # Calculate streak
    streak = calculate_streak(all_bookmarks)
    
    # Compare to yesterday
    yesterday_comparison = compare_to_yesterday(
        today_bookmarks, today_analyses, all_bookmarks, all_analyses
    )
    
    # Get day info
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_of_week = day_names[target_date.weekday()]
    greeting = get_greeting()
    
    return DailyDigest(
        date=target_date,
        generated_at=now,
        stats=stats,
        highlights=highlights,
        quick_list=quick_list,
        streak=streak,
        yesterday_comparison=yesterday_comparison,
        day_of_week=day_of_week,
        greeting=greeting
    )


def format_streak_message(streak: StreakInfo) -> str:
    """Format streak info into a motivational message."""
    if not streak.streak_active:
        return "📚 Start a new streak today!"
    
    if streak.current_streak == 1:
        return "📚 First bookmark of the streak!"
    elif streak.current_streak < 3:
        return f"🔥 {streak.current_streak} day streak"
    elif streak.current_streak < 7:
        return f"🔥 {streak.current_streak} day streak! Keep it going"
    elif streak.current_streak < 14:
        return f"🔥 {streak.current_streak} day streak! You're on fire"
    else:
        return f"🚀 {streak.current_streak} day streak! Legendary"
