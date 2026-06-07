#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rolloforge.storage import load_analysis_results, load_bookmarks, save_analysis_results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Decay stale actionable queue items into build_later.")
    parser.add_argument("--days", type=int, default=14, help="Demote items older than this many days (default: 14)")
    parser.add_argument("--apply", action="store_true", help="Persist changes. Default is dry-run.")
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N stale items (0 = no limit)")
    return parser.parse_args()


def parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def effective_bucket(analysis) -> str:
    return analysis.personalized_bucket or analysis.recommendation_bucket


def bookmark_age_days(bookmark, now: datetime) -> int | None:
    dt = parse_iso(bookmark.bookmarked_at) or parse_iso(bookmark.created_at)
    if dt is None:
        return None
    return max(0, (now - dt).days)


def main() -> int:
    args = parse_args()
    now = datetime.now(timezone.utc)

    bookmarks = {b.id: b for b in load_bookmarks()}
    analyses = load_analysis_results()

    updated = []
    stale_candidates = []
    applied = 0

    for analysis in analyses:
        bookmark = bookmarks.get(analysis.bookmark_id)
        if not bookmark:
            updated.append(analysis)
            continue

        age_days = bookmark_age_days(bookmark, now)
        if age_days is None:
            updated.append(analysis)
            continue

        current_bucket = effective_bucket(analysis)
        stale_recommendation = (
            not analysis.pinned
            and analysis.recommendation_bucket == "test_this_week"
            and age_days > args.days
        )
        should_decay = stale_recommendation and current_bucket == "test_this_week"
        should_backfill_metadata = (
            stale_recommendation
            and analysis.personalized_bucket == "build_later"
            and not analysis.decayed_at
        )
        if not should_decay and not should_backfill_metadata:
            updated.append(analysis)
            continue

        stale_candidates.append((analysis, bookmark, age_days))
        if args.limit and applied >= args.limit:
            updated.append(analysis)
            continue

        decayed = replace(
            analysis,
            personalized_bucket="build_later",
            decayed_at=analysis.decayed_at or now.isoformat(),
            decayed_from_bucket=analysis.decayed_from_bucket or analysis.recommendation_bucket,
            decay_reason=analysis.decay_reason or f"Auto-demoted after {age_days} days in actionable queue",
        )
        updated.append(decayed)
        applied += 1

    print(f"stale_candidates={len(stale_candidates)} changed={applied} threshold_days={args.days} apply={args.apply}")
    for analysis, bookmark, age_days in stale_candidates[:10]:
        title = (bookmark.title or bookmark.text or "Untitled").replace("\n", " ")[:90]
        print(f"- {analysis.bookmark_id} | {age_days}d | {title}")

    if args.apply and applied:
        save_analysis_results(updated)

    return 1 if stale_candidates and not args.apply else 0


if __name__ == "__main__":
    raise SystemExit(main())
