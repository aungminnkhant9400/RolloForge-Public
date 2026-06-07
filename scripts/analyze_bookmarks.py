from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from rolloforge.analysis import analyze_pending_bookmarks
from rolloforge.storage import (
    load_analysis_results,
    load_bookmarks,
    load_seen_bookmark_ids,
    save_seen_bookmark_ids,
    upsert_analysis_results,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze new bookmarks with LLM or fallback heuristics.")
    parser.add_argument("--limit", type=int, help="Optional max number of bookmarks to analyze in this run.")
    parser.add_argument("--force-all", action="store_true", help="Re-analyze all bookmarks instead of only unseen ones.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()

    bookmarks = load_bookmarks()
    existing_results = load_analysis_results()
    seen_ids = set() if args.force_all else load_seen_bookmark_ids()

    new_results = analyze_pending_bookmarks(
        bookmarks=bookmarks,
        existing_ids=seen_ids,
        settings=settings,
        limit=args.limit,
        force_all=args.force_all,
    )

    all_results = upsert_analysis_results(existing_results, new_results)
    save_seen_bookmark_ids({result.bookmark_id for result in all_results})
    logging.info("Stored %s total analysis result(s).", len(all_results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())