from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rolloforge.reporting import generate_report
from rolloforge.storage import load_analysis_results, load_bookmarks


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    report_path = generate_report(load_bookmarks(), load_analysis_results())
    logging.info("Generated report at %s", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
