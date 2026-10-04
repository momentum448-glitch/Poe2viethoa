from __future__ import annotations

import argparse
from pathlib import Path

from app.translation_store import build_sqlite, load_json_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("translations/dialogue.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runtime/translations.sqlite3"),
    )
    args = parser.parse_args()

    records = load_json_records(args.source)
    build_sqlite(records, args.output)
    print(f"Built {args.output} with {len(records)} records")


if __name__ == "__main__":
    main()
