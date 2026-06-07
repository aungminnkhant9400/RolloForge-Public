#!/usr/bin/env python3
"""
Digest Scheduler for RolloForge

Cron-friendly entry point for automated digest delivery.
Reads schedule from config/digest_schedule.json and triggers appropriate digests.

Usage:
    python digest_scheduler.py                    # Check schedule and send if due
    python digest_scheduler.py --schedule morning_brief  # Force specific schedule
    python digest_scheduler.py --dry-run          # Check what would be sent
    python digest_scheduler.py --list             # List all schedules
    python digest_scheduler.py --check            # Check which schedules are due

Cron Setup:
    # Run every hour to check for scheduled digests
    0 * * * * cd /home/ubuntu/RolloForge && python scripts/digest_scheduler.py >> logs/scheduler.log 2>&1

Environment Variables:
    TELEGRAM_BOT_TOKEN - Required for Telegram delivery
    TELEGRAM_CHAT_ID   - Required for Telegram delivery
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rolloforge.action_tracker import ActionTracker
from config.settings import DATA_DIR


SCHEDULE_CONFIG_PATH = PROJECT_ROOT / "config" / "digest_schedule.json"
SCHEDULE_STATE_PATH = DATA_DIR / "scheduler_state.json"


class DigestScheduler:
    """Manages scheduled digest delivery."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.config = self._load_config()
        self.state = self._load_state()
        self.tracker = ActionTracker() if self.config.get("action_tracking", {}).get("enabled") else None

    def _load_config(self) -> dict:
        """Load schedule configuration."""
        if not SCHEDULE_CONFIG_PATH.exists():
            print(f"Error: Schedule config not found at {SCHEDULE_CONFIG_PATH}")
            sys.exit(1)
        
        with open(SCHEDULE_CONFIG_PATH) as f:
            return json.load(f)

    def _load_state(self) -> dict:
        """Load scheduler state (last run times)."""
        if SCHEDULE_STATE_PATH.exists():
            with open(SCHEDULE_STATE_PATH) as f:
                return json.load(f)
        return {"last_runs": {}, "version": "1.0"}

    def _save_state(self) -> None:
        """Save scheduler state."""
        if self.dry_run:
            return
        
        SCHEDULE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULE_STATE_PATH, "w") as f:
            json.dump(self.state, f, indent=2)

    def list_schedules(self) -> None:
        """List all configured schedules."""
        print("📅 Configured Digest Schedules")
        print("=" * 50)
        
        for schedule in self.config.get("schedules", []):
            status = "✅ Enabled" if schedule.get("enabled") else "❌ Disabled"
            schedule_type = schedule.get("type", "unknown")
            time_str = schedule.get("time", "--:--")
            
            if schedule_type == "weekly":
                day = schedule.get("day", "unknown")
                when = f"{day.capitalize()}s at {time_str}"
            else:
                when = f"Daily at {time_str}"
            
            last_run = self.state.get("last_runs", {}).get(schedule["id"], "Never")
            if last_run != "Never":
                last_run_dt = datetime.fromisoformat(last_run)
                last_run = last_run_dt.strftime("%Y-%m-%d %H:%M")
            
            print(f"\n📝 {schedule['name']} ({schedule['id']})")
            print(f"   Status: {status}")
            print(f"   Schedule: {when}")
            print(f"   Format: {schedule.get('format', 'default')}")
            print(f"   Last run: {last_run}")

    def check_due(self) -> list[dict]:
        """Check which schedules are due to run."""
        now = datetime.now()
        due_schedules = []
        
        for schedule in self.config.get("schedules", []):
            if not schedule.get("enabled", False):
                continue
            
            schedule_id = schedule["id"]
            last_run_str = self.state.get("last_runs", {}).get(schedule_id)
            
            if self._is_due(schedule, last_run_str, now):
                due_schedules.append(schedule)
        
        return due_schedules

    def _is_due(self, schedule: dict, last_run_str: str | None, now: datetime) -> bool:
        """Check if a schedule is due to run."""
        schedule_type = schedule.get("type", "daily")
        schedule_time = schedule.get("time", "00:00")
        
        # Parse schedule time
        hour, minute = map(int, schedule_time.split(":"))
        
        if schedule_type == "daily":
            # Check if we've run today at or after the scheduled time
            if last_run_str:
                last_run = datetime.fromisoformat(last_run_str)
                if last_run.date() == now.date() and last_run.hour >= hour:
                    return False
            
            # Check if current time is at or after scheduled time
            return now.hour >= hour
        
        elif schedule_type == "weekly":
            schedule_day = schedule.get("day", "monday").lower()
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            target_day = days.index(schedule_day)
            current_day = now.weekday()
            
            if current_day != target_day:
                return False
            
            # Same day, check time
            if last_run_str:
                last_run = datetime.fromisoformat(last_run_str)
                if last_run.date() == now.date():
                    return False
            
            return now.hour >= hour
        
        return False

    def run_schedule(self, schedule: dict) -> bool:
        """Execute a single schedule."""
        schedule_id = schedule["id"]
        format_type = schedule.get("format", "morning")
        highlights = schedule.get("highlights", 5)
        
        print(f"\n🚀 Running schedule: {schedule['name']}")
        print(f"   Format: {format_type}, Highlights: {highlights}")
        
        if self.dry_run:
            print("   [DRY RUN - Would send digest]")
            return True
        
        try:
            # Import and run the appropriate sender
            if format_type in ["morning", "summary"]:
                from scripts.send_daily_digest import main as send_daily
                
                # Build args for daily digest
                import argparse
                daily_parser = argparse.ArgumentParser()
                daily_parser.add_argument("--date", default=None)
                daily_parser.add_argument("--format", default="morning")
                daily_parser.add_argument("--highlight", type=int, default=5)
                daily_parser.add_argument("--dry-run", action="store_true")
                daily_parser.add_argument("--save", action="store_true")
                daily_parser.add_argument("--bot-token", default=os.getenv("TELEGRAM_BOT_TOKEN"))
                daily_parser.add_argument("--chat-id", default=os.getenv("TELEGRAM_CHAT_ID"))
                daily_parser.add_argument("--topic-id", default=os.getenv("TELEGRAM_TOPIC_ID"))
                daily_args = daily_parser.parse_args([])
                daily_args.format = format_type
                daily_args.highlight = highlights
                daily_args.dry_run = self.dry_run
                
                result = send_daily(daily_args)
                if result != 0:
                    print(f"   ❌ Daily digest sender returned exit code {result}")
                    return False
            
            else:
                # Weekly/detailed digest
                from scripts.weekly_digest import main as send_weekly
                
                weekly_parser = argparse.ArgumentParser()
                weekly_parser.add_argument("--days", type=int, default=7)
                weekly_parser.add_argument("--output", default="both")
                weekly_parser.add_argument("--save", action="store_true")
                weekly_parser.add_argument("--quiet", action="store_true")
                weekly_args = weekly_parser.parse_args([])
                weekly_args.days = 7 if format_type == "detailed" else 7
                weekly_args.save = True
                
                result = send_weekly(weekly_args)
                if result != 0:
                    print(f"   ❌ Weekly digest generator returned exit code {result}")
                    return False
            
            # Update state
            self.state["last_runs"][schedule_id] = datetime.now().isoformat()
            self._save_state()
            
            print(f"   ✅ Sent successfully")
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

    def run(self, force_schedule: str | None = None) -> int:
        """Run the scheduler. Returns exit code."""
        if force_schedule:
            # Find and run specific schedule
            for schedule in self.config.get("schedules", []):
                if schedule["id"] == force_schedule:
                    self.run_schedule(schedule)
                    return 0
            print(f"Error: Schedule '{force_schedule}' not found")
            return 1
        
        # Check for due schedules
        due = self.check_due()
        
        if not due:
            print("No schedules due at this time.")
            return 0
        
        print(f"Found {len(due)} schedule(s) due to run:\n")
        
        success_count = 0
        for schedule in due:
            if self.run_schedule(schedule):
                success_count += 1
        
        print(f"\n{'=' * 50}")
        print(f"Completed: {success_count}/{len(due)} schedules successful")
        
        return 0 if success_count == len(due) else 1


def main():
    parser = argparse.ArgumentParser(
        description="Digest Scheduler for RolloForge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                    # Check and run due schedules
    %(prog)s --list             # Show all schedules
    %(prog)s --check            # Check which schedules are due (no send)
    %(prog)s --dry-run          # Dry run mode
    %(prog)s --schedule morning_brief  # Force specific schedule
        """
    )
    parser.add_argument("--list", action="store_true", help="List all schedules")
    parser.add_argument("--check", action="store_true", help="Check due schedules without sending")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (no actual sending)")
    parser.add_argument("--schedule", help="Force specific schedule by ID")
    
    args = parser.parse_args()
    
    scheduler = DigestScheduler(dry_run=args.dry_run or args.check)
    
    if args.list:
        scheduler.list_schedules()
        return 0
    
    if args.check:
        due = scheduler.check_due()
        if due:
            print(f"📅 {len(due)} schedule(s) due:")
            for s in due:
                print(f"   • {s['name']} ({s['id']})")
        else:
            print("📅 No schedules due at this time.")
        return 0
    
    return scheduler.run(force_schedule=args.schedule)


if __name__ == "__main__":
    sys.exit(main())
