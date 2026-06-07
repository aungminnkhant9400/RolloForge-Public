from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rolloforge.reporting import generate_report, summarize_recommendations
from rolloforge.storage import load_analysis_results, load_bookmarks


def main() -> int:
    bookmarks = load_bookmarks()
    analysis_results = load_analysis_results()
    report_path = generate_report(bookmarks, analysis_results)
    summary = summarize_recommendations(analysis_results)

    print("Bookmark report generated.")
    print(f"total={summary['total']}")
    print(f"test_this_week={summary['test_this_week']}")
    print(f"build_later={summary['build_later']}")
    print(f"archive={summary['archive']}")
    print(f"ignore={summary['ignore']}")
    print(f"report_path={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
