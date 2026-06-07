import json
import sys

def add_titles_to_analyses():
    """Add title field to all analyses by looking up bookmark titles."""
    # Load analyses
    with open('data/analysis_results.json', 'r') as f:
        analyses = json.load(f)
    
    # Load bookmarks for title lookup
    with open('data/bookmarks_raw.json', 'r') as f:
        bookmarks = json.load(f)
    
    # Create id -> title mapping
    title_map = {}
    for b in bookmarks:
        bid = b.get('id')
        if bid:
            title_map[bid] = b.get('title', '')
    
    # Add title to each analysis
    added = 0
    missing = 0
    for analysis in analyses:
        bid = analysis.get('bookmark_id')
        if bid and bid in title_map:
            analysis['title'] = title_map[bid]
            added += 1
        else:
            analysis['title'] = ''
            missing += 1
    
    # Save back
    with open('data/analysis_results.json', 'w') as f:
        json.dump(analyses, f, indent=2)
    
    print(f'Added titles: {added}, Missing: {missing}, Total: {len(analyses)}')
    return added, missing

if __name__ == '__main__':
    add_titles_to_analyses()
