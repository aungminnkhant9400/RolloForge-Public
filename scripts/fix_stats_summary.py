import json

def fix_stats_summary():
    """Fix stats_summary.json bucket counts to match actual analysis data."""
    # Load analyses
    with open('data/analysis_results.json', 'r') as f:
        analyses = json.load(f)
    
    # Count buckets from personalized_bucket
    bucket_counts = {}
    for a in analyses:
        bucket = a.get('personalized_bucket', a.get('recommendation_bucket', 'unknown'))
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
    
    # Load current stats
    with open('data/stats_summary.json', 'r') as f:
        stats = json.load(f)
    
    # Update counts
    before = stats.get('bucket_counts', {})
    stats['bucket_counts'] = bucket_counts
    stats['total_bookmarks'] = len(analyses)
    stats['total_analyses'] = len(analyses)
    stats['last_updated'] = '2026-05-04T08:35:00+00:00'
    
    # Save
    with open('data/stats_summary.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f'Before: {before}')
    print(f'After:  {bucket_counts}')
    print(f'Total:  {len(analyses)}')

if __name__ == '__main__':
    fix_stats_summary()
