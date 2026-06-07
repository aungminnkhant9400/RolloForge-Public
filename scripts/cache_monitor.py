#!/usr/bin/env python3
"""
Cache monitoring utility for RolloForge.

Usage:
    python cache_monitor.py           # Show current cache stats
    python cache_monitor.py --watch   # Watch mode (updates every 2s)
    python cache_monitor.py --clear   # Clear all cache
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rolloforge.storage import get_cache_stats, invalidate_cache


def format_bytes(size: float) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def show_stats():
    """Display current cache statistics."""
    stats = get_cache_stats()
    
    print("\n" + "="*50)
    print("  ROLLOFORGE CACHE MONITOR")
    print("="*50)
    
    print(f"\n📊 Performance")
    print(f"  Hit Rate:        {stats['hit_rate']:.1f}%")
    print(f"  Total Requests:  {stats['total_requests']}")
    print(f"  Cache Hits:      {stats['hits']}")
    print(f"  Cache Misses:    {stats['misses']}")
    
    print(f"\n💾 Memory")
    print(f"  Active Entries:  {stats['entries']}")
    print(f"  Memory Used:     {format_bytes(stats['memory_bytes'])}")
    
    print(f"\n📝 Operations")
    print(f"  Writes:          {stats['writes']}")
    print(f"  Invalidations:   {stats['invalidations']}")
    print(f"  Expirations:     {stats['expirations']}")
    print()


def watch_mode():
    """Continuous monitoring mode."""
    try:
        while True:
            # Clear screen (cross-platform)
            print("\033[2J\033[H", end="")
            show_stats()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n👋 Stopped.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='RolloForge Cache Monitor')
    parser.add_argument('--watch', '-w', action='store_true', help='Watch mode')
    parser.add_argument('--clear', '-c', action='store_true', help='Clear cache')
    args = parser.parse_args()
    
    if args.clear:
        count = invalidate_cache()
        print(f"✅ Cache cleared ({count} entries removed)")
        return 0
    
    if args.watch:
        watch_mode()
    else:
        show_stats()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
