#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, '/home/ubuntu/RolloForge')

from rolloforge.analysis_cleanup import clean_analysis_text
from rolloforge.models import AnalysisResult, Bookmark

BOOKMARKS = Path('/home/ubuntu/RolloForge/data/bookmarks_raw.json')
ANALYSES = Path('/home/ubuntu/RolloForge/data/analysis_results.json')


def main() -> int:
    bookmarks = {b['id']: Bookmark.from_dict(b) for b in json.loads(BOOKMARKS.read_text())}
    rows = json.loads(ANALYSES.read_text())
    changed = 0
    for row in rows:
        bookmark = bookmarks.get(row['bookmark_id'])
        if not bookmark:
            continue
        analysis = AnalysisResult.from_dict(row)
        before = (analysis.summary, analysis.recommendation_reason)
        analysis = clean_analysis_text(bookmark, analysis)
        after = (analysis.summary, analysis.recommendation_reason)
        if after != before:
            row['summary'] = analysis.summary
            row['recommendation_reason'] = analysis.recommendation_reason
            changed += 1
    ANALYSES.write_text(json.dumps(rows, indent=2) + '\n')
    print({'changed': changed})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
