#!/usr/bin/env python3
"""
Bookmark Sync Health Dashboard - Data integrity monitoring for RolloForge.

Checks:
- bookmarks.json and analysis_results.json sync status
- Missing analyses
- Duplicate URLs
- Malformed data
- Orphaned analyses

Exit codes:
  0 - All healthy
  1 - Medium issues (warnings)
  2 - Critical issues
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def load_json(path: Path) -> Tuple[bool, Any]:
    """Load JSON file, return (success, data)."""
    try:
        with open(path) as f:
            return True, json.load(f)
    except json.JSONDecodeError as e:
        return False, f"JSON error: {e}"
    except FileNotFoundError:
        return False, "File not found"
    except Exception as e:
        return False, str(e)

def check_sync(bookmarks: List[dict], analyses: List[dict]) -> Dict:
    """Check if bookmarks and analyses are in sync."""
    bookmark_ids = {b['id'] for b in bookmarks}
    analysis_ids = {a['bookmark_id'] for a in analyses}
    
    missing_analyses = bookmark_ids - analysis_ids
    orphaned_analyses = analysis_ids - bookmark_ids
    
    return {
        'bookmark_count': len(bookmarks),
        'analysis_count': len(analyses),
        'sync_rate': len(bookmark_ids & analysis_ids) / len(bookmark_ids) * 100 if bookmark_ids else 0,
        'missing_analyses': list(missing_analyses),
        'orphaned_analyses': list(orphaned_analyses),
        'in_sync': len(missing_analyses) == 0 and len(orphaned_analyses) == 0
    }

def check_duplicates(bookmarks: List[dict]) -> Dict:
    """Check for duplicate URLs."""
    urls = {}
    duplicates = []
    
    for b in bookmarks:
        url = b.get('url', '').lower().rstrip('/').split('?')[0]
        if url in urls:
            duplicates.append({
                'url': url,
                'ids': [urls[url], b['id']],
                'titles': [next(x['title'] for x in bookmarks if x['id'] == urls[url]), b['title']]
            })
        else:
            urls[url] = b['id']
    
    return {
        'total': len(bookmarks),
        'unique': len(urls),
        'duplicates': duplicates,
        'has_duplicates': len(duplicates) > 0
    }

def check_required_fields(bookmarks: List[dict]) -> List[Dict]:
    """Check bookmarks have required fields."""
    required = ['id', 'url', 'title', 'source', 'created_at']
    malformed = []
    
    for b in bookmarks:
        missing = [f for f in required if f not in b or not b[f]]
        if missing:
            malformed.append({
                'id': b.get('id', 'UNKNOWN'),
                'missing_fields': missing
            })
    
    return malformed

def check_analysis_integrity(analyses: List[dict]) -> List[Dict]:
    """Check analyses have required fields."""
    required = ['bookmark_id', 'summary', 'priority_score']
    malformed = []
    
    for a in analyses:
        missing = [f for f in required if f not in a or not a[f]]
        if missing:
            malformed.append({
                'bookmark_id': a.get('bookmark_id', 'UNKNOWN'),
                'missing_fields': missing
            })
    
    return malformed

def generate_report(checks: Dict, output_path: Path = None) -> str:
    """Generate markdown report."""
    timestamp = datetime.now().isoformat()
    
    report = f"""# Bookmark Health Report

Generated: {timestamp}

## Summary

| Metric | Value | Status |
|--------|-------|--------|
| Bookmarks | {checks['sync']['bookmark_count']} | - |
| Analyses | {checks['sync']['analysis_count']} | - |
| Sync Rate | {checks['sync']['sync_rate']:.1f}% | {'✅' if checks['sync']['in_sync'] else '⚠️'} |
| Unique URLs | {checks['duplicates']['unique']}/{checks['duplicates']['total']} | {'✅' if not checks['duplicates']['has_duplicates'] else '⚠️'} |
| Malformed Bookmarks | {len(checks['malformed_bookmarks'])} | {'✅' if not checks['malformed_bookmarks'] else '❌'} |
| Malformed Analyses | {len(checks['malformed_analyses'])} | {'✅' if not checks['malformed_analyses'] else '❌'} |

## Details

### Sync Issues
"""
    
    if checks['sync']['missing_analyses']:
        report += "\n**Missing Analyses:**\n"
        for id in checks['sync']['missing_analyses'][:10]:
            report += f"- `{id}`\n"
        if len(checks['sync']['missing_analyses']) > 10:
            report += f"- ... and {len(checks['sync']['missing_analyses']) - 10} more\n"
    else:
        report += "\n✅ No missing analyses\n"
    
    if checks['sync']['orphaned_analyses']:
        report += "\n**Orphaned Analyses (no bookmark):**\n"
        for id in checks['sync']['orphaned_analyses'][:10]:
            report += f"- `{id}`\n"
    
    if checks['duplicates']['has_duplicates']:
        report += "\n### Duplicate URLs\n"
        for dup in checks['duplicates']['duplicates'][:5]:
            report += f"- `{dup['url'][:60]}...`\n"
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)
    
    return report

def print_console_report(checks: Dict):
    """Print colored console report."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}📊 Bookmark Health Dashboard{Colors.RESET}\n")
    
    # Sync status
    sync = checks['sync']
    print(f"{Colors.BOLD}Sync Status:{Colors.RESET}")
    print(f"  Bookmarks: {sync['bookmark_count']}")
    print(f"  Analyses:  {sync['analysis_count']}")
    
    if sync['in_sync']:
        print(f"  {Colors.GREEN}✓ 100% sync rate{Colors.RESET}")
    else:
        print(f"  {Colors.YELLOW}⚠ Sync rate: {sync['sync_rate']:.1f}%{Colors.RESET}")
        if sync['missing_analyses']:
            print(f"    {Colors.YELLOW}- {len(sync['missing_analyses'])} missing analyses{Colors.RESET}")
        if sync['orphaned_analyses']:
            print(f"    {Colors.YELLOW}- {len(sync['orphaned_analyses'])} orphaned analyses{Colors.RESET}")
    
    # Duplicates
    dups = checks['duplicates']
    print(f"\n{Colors.BOLD}Duplicates:{Colors.RESET}")
    if dups['has_duplicates']:
        print(f"  {Colors.YELLOW}⚠ {len(dups['duplicates'])} duplicates found{Colors.RESET}")
    else:
        print(f"  {Colors.GREEN}✓ No duplicates{Colors.RESET}")
    
    # Malformed
    print(f"\n{Colors.BOLD}Data Quality:{Colors.RESET}")
    if checks['malformed_bookmarks']:
        print(f"  {Colors.RED}✗ {len(checks['malformed_bookmarks'])} malformed bookmarks{Colors.RESET}")
    else:
        print(f"  {Colors.GREEN}✓ All bookmarks valid{Colors.RESET}")
    
    if checks['malformed_analyses']:
        print(f"  {Colors.RED}✗ {len(checks['malformed_analyses'])} malformed analyses{Colors.RESET}")
    else:
        print(f"  {Colors.GREEN}✓ All analyses valid{Colors.RESET}")
    
    # Overall
    print(f"\n{Colors.BOLD}Overall Status:{Colors.RESET}")
    if checks['healthy']:
        print(f"  {Colors.GREEN}✅ HEALTHY{Colors.RESET}")
    elif checks['critical']:
        print(f"  {Colors.RED}❌ CRITICAL ISSUES{Colors.RESET}")
    else:
        print(f"  {Colors.YELLOW}⚠️ WARNINGS{Colors.RESET}")
    print()

def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='RolloForge Bookmark Health Dashboard')
    parser.add_argument('--report', action='store_true', help='Generate markdown report')
    parser.add_argument('--output', type=str, default='reports/bookmark_health.md', help='Report output path')
    parser.add_argument('--quiet', '-q', action='store_true', help='Minimal output')
    args = parser.parse_args()
    
    data_dir = Path('/home/ubuntu/RolloForge/data')
    bookmarks_file = data_dir / 'bookmarks_raw.json'
    analysis_file = data_dir / 'analysis_results.json'
    
    # Load data
    bookmarks_ok, bookmarks = load_json(bookmarks_file)
    analysis_ok, analyses = load_json(analysis_file)
    
    if not bookmarks_ok:
        print(f"{Colors.RED}Error loading bookmarks: {bookmarks}{Colors.RESET}")
        return 2
    
    if not analysis_ok:
        print(f"{Colors.RED}Error loading analyses: {analyses}{Colors.RESET}")
        return 2
    
    # Run checks
    sync = check_sync(bookmarks, analyses)
    duplicates = check_duplicates(bookmarks)
    malformed_bookmarks = check_required_fields(bookmarks)
    malformed_analyses = check_analysis_integrity(analyses)
    
    checks = {
        'sync': sync,
        'duplicates': duplicates,
        'malformed_bookmarks': malformed_bookmarks,
        'malformed_analyses': malformed_analyses,
        'healthy': sync['in_sync'] and not duplicates['has_duplicates'] and not malformed_bookmarks and not malformed_analyses,
        'critical': len(malformed_bookmarks) > 0 or len(malformed_analyses) > 0
    }
    
    # Output
    if not args.quiet:
        print_console_report(checks)
    
    if args.report:
        output_path = Path(args.output)
        output_path.parent.mkdir(exist_ok=True)
        generate_report(checks, output_path)
        if not args.quiet:
            print(f"{Colors.BLUE}Report saved: {output_path}{Colors.RESET}\n")
    
    # Exit code
    if checks['critical']:
        return 2
    elif not checks['healthy']:
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
