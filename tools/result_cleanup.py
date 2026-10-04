"""Preview and remove old result archives and verified duplicate diagnostics."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import zipfile

from app.runtime_lock import RuntimeLock
from tools.translation_factory import atomic_json

RESULT_NAME = re.compile(r"(?:ALPHA|QC_PHASE[234])_RESULT_[A-Za-z0-9_-]+\.zip\Z")
STAMP = re.compile(r"(?:ALPHA|QC_PHASE[234])_RESULT_(\d{8}_\d{6}(?:_\d{6})?)\.zip\Z")
CHECKPOINTS = {
    "QC_PHASE2_RESULT_20261004_175216.zip",
    "QC_PHASE3_RESULT_20261004_183317.zip",
    "QC_PHASE4_RESULT_20261004_212425_250828.zip",
    "QC_PHASE4_RESULT_20261004_223644_671889.zip",
}


def stream_sha(stream) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(256 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def file_sha(path: Path) -> str:
    with path.open("rb") as stream:
        return stream_sha(stream)


def result_files(root: Path) -> list[Path]:
    result_dir = root / "results"
    if result_dir.is_symlink():
        raise ValueError("results/ không được là symlink.")
    return [p for folder in (root, result_dir) if folder.is_dir() for p in folder.iterdir()
            if RESULT_NAME.fullmatch(p.name) and not p.is_symlink() and p.is_file()]


def protected_names(root: Path) -> set[str]:
    names = set(CHECKPOINTS)
    for pointer in ("LAST_QC_RESULT.txt", "LAST_ALPHA_RESULT.txt"):
        path = root / pointer
        if path.is_file() and not path.is_symlink():
            for line in path.read_text(encoding="utf-8").splitlines():
                name = line.strip().replace("\\", "/").rsplit("/", 1)[-1]
                if RESULT_NAME.fullmatch(name):
                    names.add(name)
    pins = root / "results/pinned.json"
    if pins.is_file() and not pins.is_symlink():
        payload = json.loads(pins.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or any(not isinstance(n, str) or not RESULT_NAME.fullmatch(n) for n in payload):
            raise ValueError("results/pinned.json cần danh sách tên ZIP hợp lệ.")
        names.update(payload)
    return names


def pin_result(root: Path, name: str) -> None:
    root = root.resolve()
    if not RESULT_NAME.fullmatch(name) or not any(p.name == name for p in result_files(root)):
        raise ValueError("Không tìm thấy ZIP kết quả hợp lệ để ghim.")
    names = protected_names(root)
    names.add(name)
    path = root / "results/pinned.json"
    if path.is_symlink():
        raise ValueError("Không ghi qua symlink pinned.json.")
    atomic_json(path, sorted(names))


def snapshot(path: Path, root: Path) -> dict:
    stat = path.stat()
    return {"path": path.relative_to(root).as_posix(), "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns, "sha256": file_sha(path)}


def duplicate_diagnostics(root: Path, archive: Path) -> dict | None:
    """Return only an exact, complete local copy already contained in a valid ZIP."""
    match = STAMP.fullmatch(archive.name)
    if not match:
        return None
    phase = "alpha" if archive.name.startswith("ALPHA_") else re.search(r"PHASE([234])", archive.name)[1]
    folder = root / "diagnostics" / (phase if phase == "alpha" else f"phase{phase}") / match[1]
    if not folder.is_dir() or any(p.is_symlink() for p in (folder, folder.parent, folder.parent.parent)):
        return None
    paths = list(folder.rglob("*"))
    if any(p.is_symlink() for p in paths):
        return None
    files = {p.relative_to(folder).as_posix(): p for p in paths if p.is_file()}
    with zipfile.ZipFile(archive) as z:
        entries = [i for i in z.infolist() if not i.is_dir()]
        if len({i.filename for i in entries}) != len(entries) or set(files) != {i.filename for i in entries}:
            return None
        verified = []
        for info in entries:
            path = files[info.filename]
            if info.file_size != path.stat().st_size:
                return None
            with z.open(info) as stream:
                digest = stream_sha(stream)
            item = snapshot(path, root)
            if item["sha256"] != digest:
                return None
            verified.append(item)
    return {"path": folder.relative_to(root).as_posix(), "files": sorted(verified, key=lambda x: x["path"])}


def plan_cleanup(root: Path, *, keep: int = 5) -> dict:
    root = root.resolve()
    if keep < 5:
        raise ValueError("Luôn giữ ít nhất 5 ZIP mới nhất.")
    files = sorted(result_files(root), key=lambda p: (p.stat().st_mtime_ns, p.name, str(p)), reverse=True)
    protected = set(files[:keep])
    names = protected_names(root)
    protected.update(p for p in files if p.name in names)
    candidates, skipped = [], []
    for path in files:
        if path in protected:
            continue
        try:
            with zipfile.ZipFile(path) as z:
                if not {"metadata.json", "summary.json"} <= set(z.namelist()) or z.testzip() is not None:
                    raise ValueError("ZIP thiếu chẩn đoán hoặc CRC lỗi")
            item = snapshot(path, root)
            item["diagnostics"] = duplicate_diagnostics(root, path)
            candidates.append(item)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            skipped.append({"path": path.relative_to(root).as_posix(), "reason": str(exc)})
    return {"schema": 1, "root": str(root), "keep": keep,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "protected": sorted(p.relative_to(root).as_posix() for p in protected),
            "candidates": candidates, "skipped": skipped,
            "bytes": sum(c["bytes"] + sum(f["bytes"] for f in (c["diagnostics"] or {}).get("files", []))
                         for c in candidates)}


def apply_cleanup(root: Path, plan: dict) -> dict:
    root = root.resolve()
    if plan.get("schema") != 1 or plan.get("root") != str(root) or plan.get("keep", 0) < 5:
        raise ValueError("Kế hoạch không thuộc bản cài này hoặc retention không hợp lệ.")
    lock = RuntimeLock(root / "runtime/overlay.lock")
    lock.acquire()
    try:
        fresh = plan_cleanup(root, keep=plan["keep"])
        allowed = {c["path"]: c for c in fresh["candidates"]}
        candidates = plan.get("candidates", [])
        if not isinstance(candidates, list) or len({c["path"] for c in candidates}) != len(candidates):
            raise ValueError("Danh sách dọn không hợp lệ/trùng.")
        # Validate the entire selection before deleting even one file.
        if any(allowed.get(c["path"]) != c for c in candidates):
            raise ValueError("File/pointer/pin đã đổi. Xem lại kế hoạch trước khi dọn.")
        deleted = []
        for item in candidates:
            copy = item["diagnostics"]
            if copy:
                folder = root / copy["path"]
                for f in copy["files"]:
                    (root / f["path"]).unlink()
                for directory in sorted((p for p in folder.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                    directory.rmdir()
                folder.rmdir()
            (root / item["path"]).unlink()
            deleted.append(item["path"])
        return {"deleted": deleted, "bytes": sum(c["bytes"] + sum(f["bytes"] for f in (c["diagnostics"] or {}).get("files", [])) for c in candidates)}
    finally:
        lock.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", type=int, default=5)
    parser.add_argument("--plan", type=Path, default=Path("factory_reports/cleanup.json"))
    parser.add_argument("--apply", action="store_true", help="Apply the previously previewed plan.")
    parser.add_argument("--pin", help="Protect a result archive by filename.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    path = args.plan if args.plan.is_absolute() else root / args.plan
    if args.pin:
        pin_result(root, args.pin)
        result = {"pinned": args.pin}
    elif args.apply:
        result = apply_cleanup(root, json.loads(path.read_text(encoding="utf-8")))
    else:
        result = plan_cleanup(root, keep=args.keep)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
