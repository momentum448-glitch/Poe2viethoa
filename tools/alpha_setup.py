"""First-run setup and a network-free readiness check for Local Alpha."""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

from app.translation_store import build_sqlite, compile_translation_records

ROOT = Path(__file__).resolve().parents[1]
SETUP_SCHEMA = 1
DEPENDENCIES = (
    "tkinter", "mss", "PIL", "rapidfuzz", "winrt.windows.foundation",
    "winrt.windows.foundation.collections", "winrt.windows.globalization",
    "winrt.windows.graphics.imaging", "winrt.windows.media.ocr",
    "winrt.windows.storage.streams",
)


def signature(root: Path) -> dict[str, object]:
    return {
        "schema": SETUP_SCHEMA,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        **{name: hashlib.sha256((root / name).read_bytes()).hexdigest()
           for name in ("requirements.txt", "sources/sources.lock.json", "translations/dialogue_vi.json")},
    }


def dependencies_available() -> bool:
    try:
        for name in DEPENDENCIES:
            importlib.import_module(name)
        return True
    except (ImportError, OSError):
        return False


def check_platform() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Local Alpha cần Windows.")
    if sys.version_info < (3, 10):
        raise RuntimeError("Cần Python 3.10 trở lên; bản đã QC dùng Python 3.12.")
    if sys.getwindowsversion().build < 19041:
        raise RuntimeError("Cần Windows 10 build 19041 trở lên để bảo vệ OCR khỏi đọc overlay.")


def database_count(root: Path) -> int:
    db = root / "runtime/translations.sqlite3"
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("Runtime DB bị lỗi.")
        count = conn.execute(
            "SELECT COUNT(*) FROM translations WHERE status IN ('approved','reviewed') "
            "AND length(trim(source)) > 0 AND length(trim(vi)) > 0"
        ).fetchone()[0]
    if count <= 0:
        raise RuntimeError("Runtime chưa có bản dịch đã duyệt.")
    return int(count)


def readiness(root: Path = ROOT, *, platform_check: bool = True) -> tuple[bool, str]:
    """Only read local files/modules. Never install or download from this path."""
    try:
        if platform_check:
            check_platform()
        cached = json.loads((root / "runtime/alpha_setup.json").read_text(encoding="utf-8"))
        if cached.get("signature") != signature(root):
            return False, "Dữ liệu hoặc môi trường đã đổi; cần chạy SETUP_ALPHA.bat."
        if not dependencies_available():
            return False, "Thiếu thư viện; hãy chạy SETUP_ALPHA.bat."
        count = database_count(root)
        return True, f"Sẵn sàng — {count} đoạn hội thoại đã dịch."
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        return False, f"Cần thiết lập: {exc}"


def prepare(root: Path = ROOT, *, refresh: bool = False, runner=subprocess.run) -> int:
    check_platform()
    wanted = signature(root)
    stamp_path = root / "runtime/alpha_setup.json"
    try:
        previous = json.loads(stamp_path.read_text(encoding="utf-8")).get("signature", {})
    except (OSError, ValueError):
        previous = {}

    if (refresh or previous.get("requirements.txt") != wanted["requirements.txt"]
            or previous.get("python") != wanted["python"] or not dependencies_available()):
        print("[1/3] Cài thư viện…", flush=True)
        runner([sys.executable, "-m", "pip", "install", "-r", str(root / "requirements.txt")],
               cwd=root, check=True)
    if not dependencies_available():
        raise RuntimeError("Thư viện chưa sẵn sàng sau khi cài đặt.")

    corpus = root / "source_data/dialogue_corpus.jsonl"
    report_path = root / "source_data/source_sync_report.json"
    lock = json.loads((root / "sources/sources.lock.json").read_text(encoding="utf-8"))
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        report = {}
    refs_match = (report.get("source_ref") == lock["sources"]["poe2_en"]["ref"]
                  and report.get("context_ref") == lock["sources"]["dialogue_context"]["ref"])
    if refresh or not corpus.exists() or not refs_match:
        print("[2/3] Đồng bộ nguồn đã pin…", flush=True)
        command = [sys.executable, "-X", "utf8", "-m", "tools.source_sync"]
        if refresh:
            command.append("--force")
        runner(command, cwd=root, check=True)

    print("[3/3] Tạo dữ liệu chạy offline…", flush=True)
    records, stats = compile_translation_records(corpus, root / "translations/dialogue_vi.json")
    if stats["missing_source"]:
        raise RuntimeError("Bản dịch không khớp nguồn đã pin. Không thay runtime hiện có.")
    if not any(r.status in {"approved", "reviewed"} for r in records):
        raise RuntimeError("Chưa có bản dịch đã duyệt để tạo runtime.")
    target = root / "runtime/translations.sqlite3"
    temporary = target.with_name(f"translations-{uuid.uuid4().hex}.tmp")
    try:
        build_sqlite(records, temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    count = database_count(root)
    temporary_stamp = stamp_path.with_suffix(".tmp")
    temporary_stamp.write_text(json.dumps({"signature": wanted, "translation_records": count},
                                         ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_stamp.replace(stamp_path)
    print(f"Sẵn sàng: {count} đoạn. Các lần chạy sau dùng dữ liệu offline.", flush=True)
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.check:
        ready, message = readiness()
        print(message)
        raise SystemExit(0 if ready else 1)
    try:
        prepare(refresh=args.refresh)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
