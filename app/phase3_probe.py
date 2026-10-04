"""60-second QC entry point for the shared replacement-overlay runtime."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from .session_runtime import run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--interval", type=float, default=0.12)
    parser.add_argument("--db", type=Path, default=Path("runtime/translations.sqlite3"))
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Phase 3 probe is Windows-only.")
    session, _ = asyncio.run(run(max(10, args.seconds), max(0.05, args.interval), args.db))
    result = json.loads((session / "summary.json").read_text(encoding="utf-8"))["result"]
    if result in {"ERROR", "INTERRUPTED"}:
        raise SystemExit(130 if result == "INTERRUPTED" else 1)


if __name__ == "__main__":
    main()
