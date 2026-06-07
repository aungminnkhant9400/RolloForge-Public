"""
Action Tracker for RolloForge

Tracks user actions on digest items (completed, dismissed, snoozed)
for personalization and stale item detection.

Usage:
    from rolloforge.action_tracker import ActionTracker
    
    tracker = ActionTracker()
    tracker.log_action("bookmark_abc123", "completed")
    
    # Check if bookmark has been acted upon
    if tracker.get_action_status("bookmark_abc123"):
        print("Already handled")
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config.settings import DATA_DIR


ACTION_LOG_PATH = DATA_DIR / "action_log.json"


@dataclass
class ActionLog:
    """A single action log entry."""
    bookmark_id: str
    action_type: str  # completed, dismissed, snoozed, clicked
    timestamp: str
    digest_id: Optional[str] = None
    source: Optional[str] = None  # telegram, web, etc.
    notes: Optional[str] = None


class ActionTracker:
    """Track and query actions on bookmarks."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or ACTION_LOG_PATH
        self._actions: list[ActionLog] = []
        self._index: dict[str, ActionLog] = {}  # bookmark_id -> latest action
        self._load()

    def _load(self) -> None:
        """Load action log from disk."""
        if not self.log_path.exists():
            return
        
        try:
            with open(self.log_path) as f:
                data = json.load(f)
            
            self._actions = [ActionLog(**entry) for entry in data.get("actions", [])]
            self._build_index()
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Could not load action log: {e}")
            self._actions = []

    def _save(self) -> None:
        """Save action log to disk."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "actions": [asdict(a) for a in self._actions]
        }
        
        # Write atomically
        temp_path = self.log_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)
        temp_path.replace(self.log_path)

    def _build_index(self) -> None:
        """Build lookup index by bookmark_id (keeps latest action)."""
        self._index = {}
        for action in self._actions:
            existing = self._index.get(action.bookmark_id)
            if not existing or action.timestamp > existing.timestamp:
                self._index[action.bookmark_id] = action

    def log_action(
        self,
        bookmark_id: str,
        action_type: str,
        digest_id: Optional[str] = None,
        source: Optional[str] = None,
        notes: Optional[str] = None
    ) -> ActionLog:
        """Log a new action."""
        action = ActionLog(
            bookmark_id=bookmark_id,
            action_type=action_type,
            timestamp=datetime.now().isoformat(),
            digest_id=digest_id,
            source=source,
            notes=notes
        )
        
        self._actions.append(action)
        self._index[bookmark_id] = action
        self._save()
        
        return action

    def get_action_status(self, bookmark_id: str) -> Optional[ActionLog]:
        """Get the latest action for a bookmark."""
        return self._index.get(bookmark_id)

    def has_been_acted_on(self, bookmark_id: str) -> bool:
        """Check if a bookmark has been acted upon."""
        action = self._index.get(bookmark_id)
        if not action:
            return False
        return action.action_type in ("completed", "dismissed")

    def get_snoozed_until(self, bookmark_id: str) -> Optional[datetime]:
        """Get snooze expiry for a bookmark."""
        action = self._index.get(bookmark_id)
        if action and action.action_type == "snoozed":
            # Default snooze is 24 hours
            action_time = datetime.fromisoformat(action.timestamp)
            return action_time + timedelta(hours=24)
        return None

    def is_snoozed(self, bookmark_id: str) -> bool:
        """Check if a bookmark is currently snoozed."""
        until = self.get_snoozed_until(bookmark_id)
        if until:
            return datetime.now() < until
        return False

    def get_stats(self, days: int = 30) -> dict:
        """Get action statistics."""
        cutoff = datetime.now() - timedelta(days=days)
        
        recent = [a for a in self._actions if datetime.fromisoformat(a.timestamp) >= cutoff]
        
        by_type = {}
        for a in recent:
            by_type[a.action_type] = by_type.get(a.action_type, 0) + 1
        
        return {
            "total_actions": len(recent),
            "by_type": by_type,
            "days": days,
            "unique_bookmarks": len(set(a.bookmark_id for a in recent))
        }

    def get_stale_items(
        self,
        bookmark_ids: list[str],
        threshold_days: int = 7
    ) -> list[dict]:
        """Find bookmarks that haven't been acted on within threshold."""
        cutoff = datetime.now() - timedelta(days=threshold_days)
        stale = []
        
        for bid in bookmark_ids:
            action = self._index.get(bid)
            if not action:
                # Never acted on
                stale.append({
                    "bookmark_id": bid,
                    "status": "never_acted",
                    "days_since": None
                })
            elif datetime.fromisoformat(action.timestamp) < cutoff:
                # Acted on but long ago
                days = (datetime.now() - datetime.fromisoformat(action.timestamp)).days
                stale.append({
                    "bookmark_id": bid,
                    "status": f"last_{action.action_type}",
                    "days_since": days,
                    "last_action": action.action_type
                })
        
        return stale

    def get_unactioned_bookmarks(self, bookmark_ids: list[str]) -> list[str]:
        """Get list of bookmark IDs that have never been acted upon."""
        return [bid for bid in bookmark_ids if bid not in self._index]

    def clear_old_actions(self, days: int = 90) -> int:
        """Remove actions older than specified days. Returns count removed."""
        cutoff = datetime.now() - timedelta(days=days)
        original_len = len(self._actions)
        
        self._actions = [
            a for a in self._actions
            if datetime.fromisoformat(a.timestamp) >= cutoff
        ]
        
        self._build_index()
        self._save()
        
        return original_len - len(self._actions)
