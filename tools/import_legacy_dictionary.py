from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def slugify(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:48] or "dialogue"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert the legacy dictionary.json into Phase 2 records."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("translations/dialogue.json"),
    )
    parser.add_argument(
        "--status",
        choices=("draft", "reviewed", "approved"),
        default="reviewed",
    )
    args = parser.parse_args()

    legacy = json.loads(args.input.read_text(encoding="utf-8-sig"))
    if not isinstance(legacy, dict):
        raise SystemExit("Legacy dictionary root must be an object keyed by English text.")

    records = []
    used_ids: set[str] = set()

    for index, (source, payload) in enumerate(legacy.items(), start=1):
        if isinstance(payload, str):
            vi = payload
            speaker = None
            context = None
        elif isinstance(payload, dict):
            vi = payload.get("vi") or payload.get("translation") or ""
            speaker = payload.get("speaker")
            context = payload.get("context")
        else:
            continue

        source = str(source).strip()
        vi = str(vi).strip()
        if not source or not vi:
            continue

        base = f"dialogue_{slugify(str(speaker or 'unknown'))}_{index:04d}"
        record_id = base
        suffix = 2
        while record_id in used_ids:
            record_id = f"{base}_{suffix}"
            suffix += 1
        used_ids.add(record_id)

        records.append(
            {
                "id": record_id,
                "source": source,
                "vi": vi,
                "speaker": str(speaker).strip() if speaker else None,
                "area": None,
                "type": "dialogue",
                "status": args.status,
                "aliases": [],
                "legacy_context": context,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Imported {len(records)} records -> {args.output}")


if __name__ == "__main__":
    main()
