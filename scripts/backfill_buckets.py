#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, '/home/ubuntu/RolloForge')

from rolloforge.bucketing import refine_bucket
from rolloforge.models import Bookmark, AnalysisResult

BOOKMARKS = Path('/home/ubuntu/RolloForge/data/bookmarks_raw.json')
ANALYSES = Path('/home/ubuntu/RolloForge/data/analysis_results.json')


def main() -> int:
    bookmarks = {b['id']: Bookmark.from_dict(b) for b in json.loads(BOOKMARKS.read_text())}
    analyses_raw = json.loads(ANALYSES.read_text())
    changed = 0
    counts = Counter()
    for row in analyses_raw:
        bookmark = bookmarks.get(row['bookmark_id'])
        if not bookmark:
            continue
        analysis = AnalysisResult.from_dict(row)
        new_bucket = refine_bucket(bookmark, analysis)
        if new_bucket != row.get('recommendation_bucket'):
            row['recommendation_bucket'] = new_bucket
            changed += 1
        counts[row['recommendation_bucket']] += 1
    ANALYSES.write_text(json.dumps(analyses_raw, indent=2) + '\n')
    print({'changed': changed, 'buckets': dict(counts)})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
