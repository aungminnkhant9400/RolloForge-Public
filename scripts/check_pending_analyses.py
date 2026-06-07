#!/usr/bin/env python3
"""Report pending or failed bookmark analyses from canonical RolloForge data files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BOOKMARKS_PATH = DATA_DIR / "bookmarks_raw.json"
ANALYSES_PATH = DATA_DIR / "analysis_results.json"


def load_json(path: Path) -> list[dict[str, Any]]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"Missing data file: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}")


def is_pending(analysis: dict[str, Any]) -> bool:
    bucket = (analysis.get("personalized_bucket") or analysis.get("recommendation_bucket") or "").strip().lower()
    source = str(analysis.get("analysis_source") or "").strip().lower()
    summary = str(analysis.get("summary") or "").strip().lower()
    reason = str(analysis.get("recommendation_reason") or "").strip().lower()

    return (
        bucket == "pending"
        or source.startswith("pending")
        or "analysis failed" in summary
        or "analysis failed" in reason
    )


def sort_key(item: dict[str, Any]) -> str:
    bookmark = item["bookmark"]
    analysis = item["analysis"]
    return (
        str(bookmark.get("bookmarked_at") or bookmark.get("created_at") or "")
        or str(analysis.get("analyzed_at") or "")
    )


def build_rows(bookmarks: list[dict[str, Any]], analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bookmarks_by_id = {bookmark.get("id"): bookmark for bookmark in bookmarks if bookmark.get("id")}
    rows: list[dict[str, Any]] = []

    for analysis in analyses:
        bookmark_id = analysis.get("bookmark_id")
        if not bookmark_id or not is_pending(analysis):
            continue
        bookmark = bookmarks_by_id.get(bookmark_id, {})
        rows.append({"bookmark": bookmark, "analysis": analysis})

    rows.sort(key=sort_key, reverse=True)
    return rows


def print_rows(rows: list[dict[str, Any]], limit: int) -> None:
    shown = rows[:limit]
    if not shown:
        print("OK: no pending or failed analyses")
        return

    print(f"PENDING_ANALYSES {len(rows)}")
    for row in shown:
        bookmark = row["bookmark"]
        analysis = row["analysis"]
        title = (bookmark.get("title") or analysis.get("title") or "Untitled").replace("\n", " ")
        ts = bookmark.get("bookmarked_at") or bookmark.get("created_at") or analysis.get("analyzed_at") or "unknown"
        bucket = analysis.get("personalized_bucket") or analysis.get("recommendation_bucket") or "unknown"
        source = analysis.get("analysis_source") or "unknown"
        summary = (analysis.get("summary") or "").replace("\n", " ")
        print(f"- {bookmark.get('id') or analysis.get('bookmark_id')} | {ts} | {bucket} | {source} | {title[:120]}")
        if summary:
            print(f"  {summary[:180]}")

    remaining = len(rows) - len(shown)
    if remaining > 0:
        print(f"... and {remaining} more")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10, help="max rows to print")
    parser.add_argument("--strict", action="store_true", help="exit 1 when pending/failed analyses exist")
    args = parser.parse_args()

    bookmarks = load_json(BOOKMARKS_PATH)
    analyses = load_json(ANALYSES_PATH)
    rows = build_rows(bookmarks, analyses)
    print_rows(rows, limit=max(args.limit, 1))

    if rows and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
