#!/usr/bin/env python3
"""
Real-world bookmark operations benchmark.
Tests load, filter, and search operations with/without cache.
"""

from __future__ import annotations

import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rolloforge.storage import (
    load_bookmarks,
    load_analysis_results,
    invalidate_cache,
    get_cache_stats,
)
from rolloforge.cache import reset_cache
from rolloforge.models import Bookmark, AnalysisResult


def benchmark_operation(name: str, iterations: int, operation, setup_fn=None):
    """Benchmark a single operation."""
    results = {
        "name": name,
        "iterations": iterations,
        "times": [],
        "total_time": 0,
        "avg_time": 0,
        "peak_mb": 0,
    }
    
    tracemalloc.start()
    start = time.perf_counter()
    
    for i in range(iterations):
        if setup_fn:
            setup_fn()
        iter_start = time.perf_counter()
        operation()
        results["times"].append(time.perf_counter() - iter_start)
    
    results["total_time"] = time.perf_counter() - start
    results["avg_time"] = sum(results["times"]) / len(results["times"])
    _, peak = tracemalloc.get_traced_memory()
    results["peak_mb"] = peak / (1024 * 1024)
    tracemalloc.stop()
    
    return results


def load_all_bookmarks_test():
    """Load all bookmarks."""
    bookmarks = load_bookmarks()
    return len(bookmarks)


def filter_by_bucket_test(bucket: str = "ai-ml"):
    """Filter bookmarks by bucket."""
    bookmarks = load_bookmarks()
    analyses = load_analysis_results()
    
    # Create analysis lookup
    analysis_map = {a.bookmark_id: a for a in analyses}
    
    # Filter by bucket
    filtered = [
        b for b in bookmarks 
        if b.id in analysis_map and analysis_map[b.id].recommendation_bucket == bucket
    ]
    return len(filtered)


def search_operations_test(query: str = "python"):
    """Search bookmarks by text."""
    bookmarks = load_bookmarks()
    analyses = load_analysis_results()
    
    query_lower = query.lower()
    results = []
    
    for bookmark in bookmarks:
        # Search in title and URL
        if query_lower in (bookmark.title or "").lower() or query_lower in (bookmark.url or "").lower():
            results.append(bookmark)
            continue
        
        # Search in analysis
        for analysis in analyses:
            if analysis.bookmark_id == bookmark.id:
                if query_lower in (analysis.summary or "").lower() or \
                   query_lower in (analysis.recommendation_reason or "").lower():
                    results.append(bookmark)
                    break
    
    return len(results)


def run_real_world_benchmarks():
    """Run all real-world benchmarks."""
    print("\n" + "="*60)
    print("  REAL-WORLD BOOKMARK OPERATIONS BENCHMARK")
    print("="*60)
    
    # Check data size
    bookmarks = load_bookmarks()
    analyses = load_analysis_results()
    print(f"\nDataset: {len(bookmarks)} bookmarks, {len(analyses)} analyses")
    
    # Get unique buckets
    analysis_map = {a.bookmark_id: a for a in analyses}
    buckets = set(a.recommendation_bucket for a in analyses if a.recommendation_bucket)
    print(f"Buckets: {sorted(buckets)[:5]}...")
    
    results = {}
    
    # Test 1: Load all bookmarks (10 iterations)
    print("\n" + "-"*60)
    print("Test 1: Load all bookmarks (10 iterations)")
    print("-"*60)
    
    # Without cache
    reset_cache()
    invalidate_cache()
    no_cache = benchmark_operation(
        "load_all_no_cache", 10, load_all_bookmarks_test,
        setup_fn=invalidate_cache
    )
    
    # With cache
    reset_cache()
    invalidate_cache()
    # Pre-load to populate cache
    load_bookmarks()
    with_cache = benchmark_operation(
        "load_all_with_cache", 10, load_all_bookmarks_test
    )
    
    print(f"  Without cache: {no_cache['total_time']:.4f}s (avg: {no_cache['avg_time']*1000:.2f}ms)")
    print(f"  With cache:    {with_cache['total_time']:.4f}s (avg: {with_cache['avg_time']*1000:.2f}ms)")
    print(f"  Speedup:       {no_cache['total_time']/with_cache['total_time']:.1f}x")
    
    results["load_all"] = (no_cache, with_cache)
    
    # Test 2: Filter by bucket (20 iterations)
    print("\n" + "-"*60)
    print("Test 2: Filter by bucket 'ai-ml' (20 iterations)")
    print("-"*60)
    
    # Without cache
    reset_cache()
    invalidate_cache()
    no_cache = benchmark_operation(
        "filter_no_cache", 20, lambda: filter_by_bucket_test("ai-ml"),
        setup_fn=invalidate_cache
    )
    
    # With cache
    reset_cache()
    invalidate_cache()
    # Pre-load
    load_bookmarks()
    load_analysis_results()
    with_cache = benchmark_operation(
        "filter_with_cache", 20, lambda: filter_by_bucket_test("ai-ml")
    )
    
    print(f"  Without cache: {no_cache['total_time']:.4f}s (avg: {no_cache['avg_time']*1000:.2f}ms)")
    print(f"  With cache:    {with_cache['total_time']:.4f}s (avg: {with_cache['avg_time']*1000:.2f}ms)")
    print(f"  Speedup:       {no_cache['total_time']/with_cache['total_time']:.1f}x")
    
    results["filter_bucket"] = (no_cache, with_cache)
    
    # Test 3: Search operations (20 iterations)
    print("\n" + "-"*60)
    print("Test 3: Search for 'python' (20 iterations)")
    print("-"*60)
    
    # Without cache
    reset_cache()
    invalidate_cache()
    no_cache = benchmark_operation(
        "search_no_cache", 20, lambda: search_operations_test("python"),
        setup_fn=invalidate_cache
    )
    
    # With cache
    reset_cache()
    invalidate_cache()
    # Pre-load
    load_bookmarks()
    load_analysis_results()
    with_cache = benchmark_operation(
        "search_with_cache", 20, lambda: search_operations_test("python")
    )
    
    print(f"  Without cache: {no_cache['total_time']:.4f}s (avg: {no_cache['avg_time']*1000:.2f}ms)")
    print(f"  With cache:    {with_cache['total_time']:.4f}s (avg: {with_cache['avg_time']*1000:.2f}ms)")
    print(f"  Speedup:       {no_cache['total_time']/with_cache['total_time']:.1f}x")
    
    results["search"] = (no_cache, with_cache)
    
    # Memory usage check
    print("\n" + "-"*60)
    print("Memory Usage Check")
    print("-"*60)
    
    reset_cache()
    invalidate_cache()
    tracemalloc.start()
    start_mem = tracemalloc.get_traced_memory()[0]
    
    # Load everything into cache
    load_bookmarks()
    load_analysis_results()
    
    cache_mem = tracemalloc.get_traced_memory()[0] - start_mem
    stats = get_cache_stats()
    
    print(f"  Cache entries:      {stats['entries']}")
    print(f"  Memory usage:       {stats['memory_mb']:.4f} MB")
    print(f"  Memory (tracemalloc): {cache_mem / (1024*1024):.4f} MB")
    print(f"  Per entry:          {(cache_mem / stats['entries'] / 1024):.2f} KB" if stats['entries'] else "  N/A")
    
    tracemalloc.stop()
    
    return results


if __name__ == "__main__":
    run_real_world_benchmarks()
