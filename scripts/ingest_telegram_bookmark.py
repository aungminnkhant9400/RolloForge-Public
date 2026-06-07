from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from rolloforge.telegram_ingest import ingest_telegram_bookmark_message


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a structured Telegram /bookmark message.")
    parser.add_argument("--message", help="Full Telegram message content.")
    parser.add_argument("--file", help="Path to a file containing the Telegram message.")
    return parser.parse_args()


def load_message(args: argparse.Namespace) -> str:
    if args.message:
        return args.message
    if args.file:
        return Path(args.file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise RuntimeError("Provide a Telegram message with --message, --file, or stdin.")


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    message = load_message(args)

    _, _, confirmation = ingest_telegram_bookmark_message(message, settings)
    print("Bookmark saved.")
    print(f"status={confirmation['status']}")
    print(f"source={confirmation['source']}")
    print(f"capture_mode={confirmation['capture_mode']}")
    print(f"tag={confirmation['tag']}")
    print(f"recommendation={confirmation['recommendation']}")
    print(f"priority={confirmation['priority']}")
    print(f"next_action={confirmation['next_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
