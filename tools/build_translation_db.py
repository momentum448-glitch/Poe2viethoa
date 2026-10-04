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
    build_sqlite(records, args.output)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"Built {args.output}")


if __name__ == "__main__":
    main()
