from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.translation_store import build_sqlite, compile_translation_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("source_data/dialogue_corpus.jsonl"),
    )
    parser.add_argument(
        "--translations",
        type=Path,
        default=Path("translations/dialogue_vi.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runtime/translations.sqlite3"),
    )
    args = parser.parse_args()

    records, stats = compile_translation_records(args.corpus, args.translations)
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    if stats["missing_source"] > 0:
        raise SystemExit(
            f"ERROR: {stats['missing_source']} Vietnamese translation entry/entries "
            "do not exist in the synced source corpus. Refresh/remap before building."
        )

    build_sqlite(records, args.output)
    print(f"Built {args.output}")


if __name__ == "__main__":
    main()
