from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rolloforge.reporting import summarize_recommendations
from rolloforge.storage import load_analysis_results


def main() -> int:
    summary = summarize_recommendations(load_analysis_results())
    print(f"total={summary['total']}")
    print(f"test_this_week={summary['test_this_week']}")
    print(f"build_later={summary['build_later']}")
    print(f"archive={summary['archive']}")
    print(f"ignore={summary['ignore']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
