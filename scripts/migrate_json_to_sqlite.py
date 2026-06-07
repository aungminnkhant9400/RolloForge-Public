#!/usr/bin/env python3
"""
One-shot migration: import current JSON data files into SQLite.

Usage:
    python scripts/migrate_json_to_sqlite.py          # dry-run (default)
    python scripts/migrate_json_to_sqlite.py --commit  # actually write
    python scripts/migrate_json_to_sqlite.py --verify   # compare JSON vs SQLite

Safe to run multiple times — uses INSERT OR REPLACE (idempotent).
JSON files are never modified. The database file is created next to them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rolloforge.db import DB_PATH, init_db, db_exists
from rolloforge.storage import (
    load_bookmarks as json_load_bookmarks,
    load_analysis_results as json_load_analyses,
    load_known_bookmark_ids as json_load_known_ids,
    load_seen_bookmark_ids as json_load_seen_ids,
)
from rolloforge.storage_sqlite import (
    import_bookmarks_bulk,
    import_analyses_bulk,
    import_seen_bookmarks_bulk,
    load_bookmarks as sqlite_load_bookmarks,
    load_analysis_results as sqlite_load_analyses,
    load_known_bookmark_ids as sqlite_load_known_ids,
    load_seen_bookmark_ids as sqlite_load_seen_ids,
    load_stats_summary,
)


def dry_run():
    print("═══ DRY RUN — reading JSON sources (no writes) ═══\n")

    bm = json_load_bookmarks()
    ar = json_load_analyses()
    known = json_load_known_ids()
    seen = json_load_seen_ids()

    print(f"  bookmarks:     {len(bm)}")
    print(f"  analyses:      {len(ar)}")
    print(f"  known ids:     {len(known)}")
    print(f"  seen ids:      {len(seen)}")
    print(f"\n  → target DB:   {DB_PATH}")
    print(f"  → DB exists?   {db_exists()}")
    print("\nRun with --commit to perform the actual import.")


def commit_import():
    print("═══ IMPORTING JSON → SQLite ═══\n")

    bm = json_load_bookmarks()
    ar = json_load_analyses()
    known = json_load_known_ids()
    seen = json_load_seen_ids()

    init_db()

    n_bm = import_bookmarks_bulk(bm)
    print(f"  ✓ bookmarks imported:     {n_bm}")

    n_ar = import_analyses_bulk(ar)
    print(f"  ✓ analyses imported:      {n_ar}")

    import_seen_bookmarks_bulk(known, seen)
    print(f"  ✓ known IDs imported:     {len(known)}")
    print(f"  ✓ seen IDs imported:      {len(seen)}")

    stats = load_stats_summary()
    print(f"\n  stats_summary: {stats}")
    print(f"\n✅ Migration complete. Database: {DB_PATH}")


def verify():
    print("═══ VERIFY — comparing JSON vs SQLite ═══\n")

    if not db_exists():
        print("❌ Database does not exist. Run --commit first.")
        return

    j_bm = json_load_bookmarks()
    s_bm = sqlite_load_bookmarks()
    print(f"  bookmarks:    JSON={len(j_bm)}  SQLite={len(s_bm)}  {'✅' if len(j_bm) == len(s_bm) else '❌'}")

    if len(j_bm) != len(s_bm):
        j_ids = {b.id for b in j_bm}
        s_ids = {b.id for b in s_bm}
        missing_s = j_ids - s_ids
        extra_s = s_ids - j_ids
        if missing_s:
            print(f"    ⚠️  Missing in SQLite: {len(missing_s)}")
        if extra_s:
            print(f"    ⚠️  Extra in SQLite:   {len(extra_s)}")

    j_ar = json_load_analyses()
    s_ar = sqlite_load_analyses()
    print(f"  analyses:     JSON={len(j_ar)}  SQLite={len(s_ar)}  {'✅' if len(j_ar) == len(s_ar) else '❌'}")

    if len(j_ar) != len(s_ar):
        j_ids = {a.bookmark_id for a in j_ar}
        s_ids = {a.bookmark_id for a in s_ar}
        missing_s = j_ids - s_ids
        extra_s = s_ids - j_ids
        if missing_s:
            print(f"    ⚠️  Missing in SQLite: {len(missing_s)}")
        if extra_s:
            print(f"    ⚠️  Extra in SQLite:   {len(extra_s)}")

    j_known = json_load_known_ids()
    s_known = sqlite_load_known_ids()
    print(f"  known IDs:    JSON={len(j_known)}  SQLite={len(s_known)}  {'✅' if j_known == s_known else '❌'}")

    j_seen = json_load_seen_ids()
    s_seen = sqlite_load_seen_ids()
    print(f"  seen IDs:     JSON={len(j_seen)}  SQLite={len(s_seen)}  {'✅' if j_seen == s_seen else '❌'}")

    # Spot check: first bookmark fields match
    if j_bm and s_bm:
        j0 = j_bm[0]
        s0 = s_bm[0]
        all_ok = True
        for field in ("id", "url", "source", "title", "text"):
            jv = getattr(j0, field, None)
            sv = getattr(s0, field, None)
            ok = jv == sv
            if not ok:
                print(f"    ❌ {field}: JSON={jv!r}  SQLite={sv!r}")
                all_ok = False
        if all_ok:
            print(f"  spot check:   first bookmark fields match ✅")

    # Stats summary
    stats = load_stats_summary()
    print(f"\n  stats_summary: total_bookmarks={stats.get('total_bookmarks')}, "
          f"total_analyses={stats.get('total_analyses')}")


def main():
    parser = argparse.ArgumentParser(description="Migrate RolloForge JSON data to SQLite")
    parser.add_argument("--commit", action="store_true", help="Perform the actual import")
    parser.add_argument("--verify", action="store_true", help="Compare JSON vs SQLite after import")
    args = parser.parse_args()

    if args.verify:
        verify()
    elif args.commit:
        commit_import()
    else:
        dry_run()


if __name__ == "__main__":
    main()
