from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from rolloforge.storage import (
    load_bookmarks,
    load_known_bookmark_ids,
    merge_bookmarks,
    save_bookmarks,
    save_known_bookmark_ids,
)
from rolloforge.x_client import XBookmarkClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync X bookmarks into data/bookmarks_raw.json")
    parser.add_argument("--source-file", help="Optional local JSON file to import instead of the configured source.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and normalize bookmarks without writing JSON files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    client = XBookmarkClient(settings)
    logging.info("X auth config present: %s", client.auth_summary())

    existing = load_bookmarks()
    known_before = load_known_bookmark_ids()
    incoming, mode = client.fetch_bookmarks(source_file=args.source_file)
    incoming_ids = {bookmark.id for bookmark in incoming}
    existing_ids = {bookmark.id for bookmark in existing}
    new_ids = incoming_ids - existing_ids

    logging.info("Sync mode resolved to: %s", mode)
    logging.info("Fetched %s bookmark(s).", len(incoming))
    logging.info("New bookmarks detected: %s", len(new_ids))

    if args.dry_run:
        logging.info("Dry run enabled. No files were written.")
        return 0

    merged = merge_bookmarks(existing, incoming)
    save_bookmarks(merged)
    save_known_bookmark_ids(known_before | {bookmark.id for bookmark in merged})

    logging.info(
        "Stored %s total bookmark(s) in data/bookmarks_raw.json.",
        len(merged),
    )
    logging.info("Stored %s known bookmark ID(s) in data/seen_bookmarks.json.", len(known_before | {bookmark.id for bookmark in merged}))
    logging.info("New bookmarks stored: %s", len(new_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
