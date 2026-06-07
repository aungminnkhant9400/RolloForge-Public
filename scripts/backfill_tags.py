#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, '/home/ubuntu/RolloForge')

from rolloforge.tagging import clean_tags

DATA = Path('/home/ubuntu/RolloForge/data/bookmarks_raw.json')


def main() -> int:
    bookmarks = json.loads(DATA.read_text())
    changed = 0
    counter = Counter()
    for bookmark in bookmarks:
        old_tags = bookmark.get('tags', [])
        new_tags = clean_tags(
            old_tags,
            bookmark.get('title'),
            bookmark.get('text'),
            bookmark.get('url'),
            bookmark.get('note'),
            bookmark.get('author'),
        )
        if new_tags != old_tags:
            bookmark['tags'] = new_tags
            changed += 1
        for tag in bookmark.get('tags', []):
            counter[tag] += 1
    DATA.write_text(json.dumps(bookmarks, indent=2) + '\n')
    print({'changed': changed, 'top_tags': counter.most_common(15)})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
