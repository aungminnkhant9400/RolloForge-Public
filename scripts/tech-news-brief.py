#!/usr/bin/env python3
"""
Morning Tech News Briefing
Fetches and summarizes tech news from multiple sources.
Sends concise briefing via Telegram.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Telegram config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# News sources
SOURCES = {
    "hackernews": "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=5",
    "techcrunch": None,  # Requires API key
}


def fetch_hackernews():
    """Fetch top Hacker News stories."""
    try:
        resp = requests.get(SOURCES["hackernews"], timeout=30)
        resp.raise_for_status()
        data = resp.json()
        stories = []
        for hit in data.get("hits", [])[:5]:
            stories.append({
                "title": hit.get("title", "No title"),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "score": hit.get("points", 0),
                "comments": hit.get("num_comments", 0),
            })
        return stories
    except Exception as e:
        print(f"Error fetching HN: {e}", file=sys.stderr)
        return []


def fetch_github_trending():
    """Fetch trending GitHub repos."""
    try:
        # GitHub API - trending is tricky, use search for recently starred
        url = "https://api.github.com/search/repositories?q=created:>2026-03-24&sort=stars&order=desc&per_page=5"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        repos = []
        for item in data.get("items", [])[:5]:
            repos.append({
                "name": item.get("full_name", ""),
                "desc": item.get("description", "No description"),
                "stars": item.get("stargazers_count", 0),
                "url": item.get("html_url", ""),
            })
        return repos
    except Exception as e:
        print(f"Error fetching GitHub: {e}", file=sys.stderr)
        return []


def format_briefing(hn_stories, gh_repos):
    """Format the tech news briefing."""
    lines = [
        "📰 Morning Tech Briefing",
        f"🕘 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "🔥 Hacker News Top 5",
        "─" * 30,
    ]
    
    for i, story in enumerate(hn_stories, 1):
        lines.append(f"{i}. {story['title']}")
        lines.append(f"   ⬆️ {story['score']} pts | 💬 {story['comments']} comments")
        lines.append(f"   🔗 {story['url']}")
        lines.append("")
    
    if gh_repos:
        lines.append("📦 Trending GitHub Repos")
        lines.append("─" * 30)
        for i, repo in enumerate(gh_repos, 1):
            desc = repo['desc'] or "No description"
            lines.append(f"{i}. {repo['name']}")
            lines.append(f"   ⭐ {repo['stars']} stars")
            lines.append(f"   {desc[:60]}...")
            lines.append(f"   🔗 {repo['url']}")
            lines.append("")
    
    lines.append("─" * 30)
    lines.append("💡 Tip: Reply with a number (1-5) to save to RolloForge")
    
    return "\n".join(lines)


def send_telegram(message: str):
    """Send message via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Telegram not configured", file=sys.stderr)
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True,
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending Telegram: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    print("Fetching tech news...")
    
    hn_stories = fetch_hackernews()
    gh_repos = fetch_github_trending()
    
    if not hn_stories and not gh_repos:
        print("No news fetched")
        return 1
    
    briefing = format_briefing(hn_stories, gh_repos)
    
    # Send to Telegram
    if send_telegram(briefing):
        print("✓ Tech briefing sent")
        return 0
    else:
        # Fallback to stdout
        print(briefing)
        return 1


if __name__ == "__main__":
    sys.exit(main())
