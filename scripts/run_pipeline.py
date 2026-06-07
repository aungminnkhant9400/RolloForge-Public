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
from rolloforge.reporting import generate_report
from rolloforge.storage import (
    load_analysis_results,
    load_bookmarks,
    load_known_bookmark_ids,
    load_seen_bookmark_ids,
    merge_bookmarks,
    save_bookmarks,
    save_known_bookmark_ids,
    save_seen_bookmark_ids,
    upsert_analysis_results,
)
from rolloforge.x_client import XBookmarkClient

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full RolloForge pipeline.")
    parser.add_argument("--skip-sync", action="store_true", help="Skip bookmark sync and analyze existing local JSON only.")
    parser.add_argument("--source-file", help="Optional local JSON file to import for the sync step.")
    parser.add_argument("--limit", type=int, help="Optional max number of bookmarks to analyze in this run.")
    parser.add_argument("--force-all", action="store_true", help="Re-analyze all bookmarks instead of only unseen ones.")
    return parser.parse_args()


def run_sync_step(settings, args) -> tuple[list, bool]:
    """
    Run the bookmark sync step with graceful error handling.
    
    Returns:
        Tuple of (bookmarks list, success bool)
    """
    try:
        x_client = XBookmarkClient(settings)
        LOGGER.info("X auth config present: %s", x_client.auth_summary())
        
        known_before = load_known_bookmark_ids()
        
        try:
            synced, mode = x_client.fetch_bookmarks(source_file=args.source_file)
        except FileNotFoundError as e:
            LOGGER.error(f"Source file not found: {e}")
            return load_bookmarks(), False
        except Exception as e:
            LOGGER.error(f"Failed to fetch bookmarks: {e}")
            return load_bookmarks(), False
        
        bookmarks = load_bookmarks()
        new_ids = {bookmark.id for bookmark in synced} - {bookmark.id for bookmark in bookmarks}
        bookmarks = merge_bookmarks(bookmarks, synced)
        
        try:
            save_bookmarks(bookmarks)
            save_known_bookmark_ids(known_before | {bookmark.id for bookmark in bookmarks})
        except Exception as e:
            LOGGER.error(f"Failed to save bookmarks: {e}")
            # Continue with in-memory bookmarks
        
        LOGGER.info("Sync mode resolved to: %s", mode)
        LOGGER.info("Fetched %s bookmark(s).", len(synced))
        LOGGER.info("New bookmarks stored: %s", len(new_ids))
        LOGGER.info("Sync step complete with %s stored bookmark(s).", len(bookmarks))
        return bookmarks, True
        
    except Exception as e:
        LOGGER.error(f"Sync step failed: {e}")
        bookmarks = load_bookmarks()
        LOGGER.info("Continuing with %s existing bookmarks", len(bookmarks))
        return bookmarks, False


def run_analysis_step(bookmarks, args, settings) -> tuple[list, bool]:
    """
    Run the analysis step with graceful error handling.
    
    Returns:
        Tuple of (results list, success bool)
    """
    try:
        seen_ids = set() if args.force_all else load_seen_bookmark_ids()
    except Exception as e:
        LOGGER.warning(f"Could not load seen bookmark IDs: {e}")
        seen_ids = set()
    
    try:
        existing_results = load_analysis_results()
    except Exception as e:
        LOGGER.warning(f"Could not load existing results: {e}")
        existing_results = []
    
    try:
        new_results = analyze_pending_bookmarks(
            bookmarks=bookmarks,
            existing_ids=seen_ids,
            settings=settings,
            limit=args.limit,
            force_all=args.force_all,
        )
    except Exception as e:
        LOGGER.error(f"Analysis step failed: {e}")
        return existing_results, False
    
    all_results = upsert_analysis_results(existing_results, new_results)
    
    try:
        save_seen_bookmark_ids({result.bookmark_id for result in all_results})
    except Exception as e:
        LOGGER.error(f"Failed to save seen bookmark IDs: {e}")
    
    LOGGER.info("Analysis step complete: %s total results", len(all_results))
    return all_results, True


def run_report_step(bookmarks, all_results) -> tuple[Optional[Path], bool]:
    """
    Run the report generation step with graceful error handling.
    
    Returns:
        Tuple of (report path or None, success bool)
    """
    try:
        report_path = generate_report(bookmarks, all_results)
        LOGGER.info("Report written to %s", report_path)
        return report_path, True
    except Exception as e:
        LOGGER.error(f"Report generation failed: {e}")
        return None, False


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()

    overall_success = True

    # Load existing bookmarks
    bookmarks = load_bookmarks()
    LOGGER.info("Loaded %s existing bookmarks", len(bookmarks))

    # Sync step
    if not args.skip_sync:
        bookmarks, sync_success = run_sync_step(settings, args)
        if not sync_success:
            LOGGER.warning("Sync step had issues, continuing with existing data")
            overall_success = False
    else:
        LOGGER.info("Skipping sync step as requested")

    if not bookmarks:
        LOGGER.warning("No bookmarks to analyze")
        return 0

    # Analysis step
    all_results, analysis_success = run_analysis_step(bookmarks, args, settings)
    if not analysis_success:
        LOGGER.warning("Analysis step had issues")
        overall_success = False

    # Report step
    report_path, report_success = run_report_step(bookmarks, all_results)
    if not report_success:
        LOGGER.warning("Report generation had issues")
        overall_success = False

    if overall_success:
        LOGGER.info("Pipeline completed successfully")
        return 0
    else:
        LOGGER.warning("Pipeline completed with some issues")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        LOGGER.info("Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        LOGGER.exception("Pipeline failed with unexpected error")
        sys.exit(1)