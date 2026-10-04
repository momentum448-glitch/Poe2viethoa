from __future__ import annotations

import argparse
import json
from pathlib import Path
import uuid

from app.translation_store import build_sqlite, compile_translation_records


def build_database(corpus: Path, translations: Path, output: Path) -> dict[str, int]:
    records, stats = compile_translation_records(corpus, translations)
    if stats["missing_source"]:
        raise ValueError("Vietnamese entries are absent from the pinned source; runtime preserved.")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"translations-{uuid.uuid4().hex}.tmp")
    try:
        build_sqlite(records, temporary)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return stats


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

    stats = build_database(args.corpus, args.translations, args.output)
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    print(f"Built {args.output}")


if __name__ == "__main__":
    main()
