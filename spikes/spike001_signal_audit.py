from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

ZONE_RE = re.compile(r'Generating level\s+\d+\s+area\s+"([^"]+)"', re.IGNORECASE)


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, data: Any) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())


def token_overlap(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z0-9']+", normalize_text(a)))
    tb = set(re.findall(r"[a-z0-9']+", normalize_text(b)))
    if not ta or not tb:
        return 0.0
    common = len(ta & tb)
    precision = common / len(ta)
    recall = common / len(tb)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def extract_dialogue_candidate(line: str) -> dict[str, str] | None:
    """Heuristic only. We keep raw log evidence even when this returns None."""
    tail = line.rsplit("]", 1)[-1].strip()
    if not tail or ":" not in tail:
        return None

    speaker, text = tail.split(":", 1)
    speaker = speaker.strip()
    text = text.strip()
    if not (2 <= len(speaker) <= 80 and len(text) >= 2):
        return None

    noisy_prefixes = (
        "http",
        "generating level",
        "set source",
        "loading",
        "connected to",
        "finished",
        "warning",
        "error",
    )
    if speaker.casefold().startswith(noisy_prefixes):
        return None

    return {"speaker": speaker, "text": text}


def candidate_log_paths(explicit: str | None) -> list[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(os.path.expandvars(os.path.expanduser(explicit))))

    user = Path(os.environ.get("USERPROFILE", str(Path.home())))
    candidates.extend(
        [
            user / "Documents" / "My Games" / "Path of Exile 2" / "logs" / "Client.txt",
            user / "Documents" / "My Games" / "Path of Exile 2" / "Logs" / "Client.txt",
        ]
    )

    for drive in ("C:", "D:", "E:", "F:"):
        base = Path(drive + os.sep)
        candidates.extend(
            [
                base / "Program Files (x86)" / "Steam" / "steamapps" / "common" / "Path of Exile 2" / "logs" / "Client.txt",
                base / "Program Files" / "Steam" / "steamapps" / "common" / "Path of Exile 2" / "logs" / "Client.txt",
                base / "SteamLibrary" / "steamapps" / "common" / "Path of Exile 2" / "logs" / "Client.txt",
                base / "Program Files (x86)" / "Grinding Gear Games" / "Path of Exile 2" / "logs" / "Client.txt",
                base / "Program Files" / "Grinding Gear Games" / "Path of Exile 2" / "logs" / "Client.txt",
                base / "Program Files (x86)" / "Grinding Gear Games" / "logs" / "Client.txt",
            ]
        )

    seen: set[str] = set()
    unique: list[Path] = []
    for path in candidates:
        key = str(path).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def detect_log_path(explicit: str | None) -> tuple[Path | None, list[Path]]:
    existing = [p for p in candidate_log_paths(explicit) if p.is_file()]
    existing.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return (existing[0] if existing else None), existing


def parse_region(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    try:
        parts = tuple(int(v.strip()) for v in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--region must be x,y,w,h") from exc
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        raise argparse.ArgumentTypeError("--region must be x,y,w,h with positive w/h")
    return parts


class WindowsOcr:
    def __init__(self) -> None:
        self.available = False
        self.error: str | None = None
        self.engine = None
        try:
            from winrt.windows.media.ocr import OcrEngine

            self.OcrEngine = OcrEngine
            self.engine = OcrEngine.try_create_from_user_profile_languages()
            if self.engine is None:
                self.error = "Windows OCR engine returned None. Install English OCR language capability."
            else:
                self.available = True
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"

    async def recognize_bgra(self, bgra: bytes, width: int, height: int) -> dict[str, Any]:
        if not self.available or self.engine is None:
            raise RuntimeError(self.error or "Windows OCR unavailable")

        from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
        from winrt.windows.storage.streams import DataWriter

        writer = DataWriter()
        try:
            try:
                writer.write_bytes(bgra)
            except TypeError:
                writer.write_bytes(list(bgra))
            bitmap = SoftwareBitmap(BitmapPixelFormat.BGRA8, width, height)
            bitmap.copy_from_buffer(writer.detach_buffer())
            result = await self.engine.recognize_async(bitmap)
        finally:
            try:
                writer.close()
            except Exception:
                pass

        lines: list[dict[str, Any]] = []
        for line in result.lines:
            words = []
            xs: list[float] = []
            ys: list[float] = []
            x2s: list[float] = []
            y2s: list[float] = []
            for word in line.words:
                rect = word.bounding_rect
                item = {
                    "text": word.text,
                    "x": float(rect.x),
                    "y": float(rect.y),
                    "w": float(rect.width),
                    "h": float(rect.height),
                }
                words.append(item)
                xs.append(item["x"])
                ys.append(item["y"])
                x2s.append(item["x"] + item["w"])
                y2s.append(item["y"] + item["h"])

            bbox = None
            if words:
                bbox = {
                    "x": min(xs),
                    "y": min(ys),
                    "w": max(x2s) - min(xs),
                    "h": max(y2s) - min(ys),
                }
            lines.append({"text": line.text, "bbox": bbox, "words": words})

        return {"text": result.text, "lines": lines}


@dataclass
class Stats:
    started_monotonic: float = field(default_factory=time.monotonic)
    log_lines: int = 0
    zone_events: int = 0
    dialogue_candidates: int = 0
    ocr_attempts: int = 0
    ocr_frames_saved: int = 0
    unique_ocr_texts: set[str] = field(default_factory=set)
    log_dialogues: list[dict[str, str]] = field(default_factory=list)
    ocr_texts: list[str] = field(default_factory=list)


async def run(args: argparse.Namespace) -> Path:
    try:
        import mss
        from PIL import Image
    except Exception as exc:
        raise SystemExit(
            "Missing capture dependencies. Run setup_spike001.bat first. "
            f"Details: {type(exc).__name__}: {exc}"
        ) from exc

    root = Path(__file__).resolve().parents[1]
    session_dir = root / "diagnostics" / "spike001" / now_stamp()
    screenshots_dir = session_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    log_path, all_logs = detect_log_path(args.log)
    ocr = WindowsOcr()
    stats = Stats()

    metadata = {
        "started_at_local": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version,
        "platform": platform.platform(),
        "duration_requested_seconds": args.seconds,
        "capture_interval_seconds": args.interval,
        "explicit_region": args.region,
        "selected_log_path": str(log_path) if log_path else None,
        "detected_log_paths": [str(p) for p in all_logs],
        "windows_ocr_available": ocr.available,
        "windows_ocr_error": ocr.error,
    }
    write_json(session_dir / "metadata.json", metadata)

    print(f"[session] {session_dir}")
    if log_path:
        print(f"[log] {log_path}")
    else:
        print("[log] Client.txt not found automatically. OCR/capture will still run.")
        print("[log] Re-run with --log \"X:\\...\\logs\\Client.txt\" if needed.")

    if ocr.available:
        print("[ocr] Windows OCR ready")
    else:
        print(f"[ocr] unavailable: {ocr.error}")
        print("[ocr] Log + screenshot evidence will still be collected.")

    log_file = None
    if log_path:
        log_file = log_path.open("r", encoding="utf-8", errors="replace")
        log_file.seek(0, os.SEEK_END)

    last_ocr_norm = ""
    last_screenshot_save = 0.0

    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            if args.region:
                x, y, w, h = args.region
                region = {"left": x, "top": y, "width": w, "height": h}
            else:
                region = {
                    "left": monitor["left"] + round(monitor["width"] * 0.14),
                    "top": monitor["top"] + round(monitor["height"] * 0.38),
                    "width": round(monitor["width"] * 0.66),
                    "height": round(monitor["height"] * 0.28),
                }

            metadata["primary_monitor"] = dict(monitor)
            metadata["capture_region"] = region
            write_json(session_dir / "metadata.json", metadata)

            deadline = time.monotonic() + args.seconds
            frame_no = 0

            while time.monotonic() < deadline:
                loop_start = time.monotonic()

                if log_file:
                    new_lines = log_file.readlines()
                    if new_lines:
                        with (session_dir / "client_new.log").open("a", encoding="utf-8") as out:
                            for raw in new_lines:
                                line = raw.rstrip("\r\n")
                                out.write(line + "\n")
                                stats.log_lines += 1

                                zone = ZONE_RE.search(line)
                                if zone:
                                    stats.zone_events += 1
                                    append_jsonl(
                                        session_dir / "zone_events.jsonl",
                                        {"line": line, "area_id": zone.group(1)},
                                    )

                                candidate = extract_dialogue_candidate(line)
                                if candidate:
                                    stats.dialogue_candidates += 1
                                    stats.log_dialogues.append(candidate)
                                    append_jsonl(
                                        session_dir / "log_candidates.jsonl",
                                        {"line": line, **candidate},
                                    )

                shot = sct.grab(region)
                frame_no += 1
                stats.ocr_attempts += 1
                ocr_data: dict[str, Any] | None = None
                ocr_error: str | None = None

                if ocr.available:
                    try:
                        ocr_data = await ocr.recognize_bgra(
                            bytes(shot.bgra), shot.width, shot.height
                        )
                    except Exception as exc:
                        ocr_error = f"{type(exc).__name__}: {exc}"

                text = (ocr_data or {}).get("text", "")
                norm = normalize_text(text)
                should_save = False
                if norm and norm != last_ocr_norm:
                    should_save = True
                elif time.monotonic() - last_screenshot_save >= 15.0:
                    should_save = True

                if should_save:
                    ts = datetime.now().strftime("%H%M%S_%f")[:-3]
                    image_path = screenshots_dir / f"{frame_no:04d}_{ts}.png"
                    image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                    image.save(image_path)

                    record = {
                        "frame": frame_no,
                        "time_local": datetime.now().isoformat(timespec="milliseconds"),
                        "screenshot": str(image_path.relative_to(session_dir)),
                        "region": region,
                        "text": text,
                        "lines": (ocr_data or {}).get("lines", []),
                        "ocr_error": ocr_error,
                    }
                    append_jsonl(session_dir / "ocr_frames.jsonl", record)
                    stats.ocr_frames_saved += 1
                    last_screenshot_save = time.monotonic()

                    if norm:
                        stats.unique_ocr_texts.add(norm)
                        stats.ocr_texts.append(text)
                        last_ocr_norm = norm

                elapsed = time.monotonic() - loop_start
                await asyncio.sleep(max(0.05, args.interval - elapsed))
    except KeyboardInterrupt:
        print("\n[stop] Ctrl+C received; writing summary...")
    finally:
        if log_file:
            log_file.close()

    overlaps: list[dict[str, Any]] = []
    for dialogue in stats.log_dialogues:
        best_score = 0.0
        best_ocr = ""
        for ocr_text in stats.ocr_texts:
            score = token_overlap(dialogue["text"], ocr_text)
            if score > best_score:
                best_score = score
                best_ocr = ocr_text
        if best_score >= 0.35:
            overlaps.append(
                {
                    "speaker": dialogue["speaker"],
                    "log_text": dialogue["text"],
                    "best_ocr_text": best_ocr,
                    "token_f1": round(best_score, 3),
                }
            )

    write_json(session_dir / "overlap_candidates.json", overlaps)

    if stats.dialogue_candidates >= 3 and len(overlaps) >= 2:
        decision_hint = "LOG_OR_HYBRID_PROMISING"
    elif stats.zone_events >= 1 and stats.ocr_frames_saved >= 1:
        decision_hint = "HYBRID_OR_OCR_FIRST"
    else:
        decision_hint = "INSUFFICIENT_EVIDENCE"

    summary = {
        "finished_at_local": datetime.now().isoformat(timespec="seconds"),
        "duration_seconds": round(time.monotonic() - stats.started_monotonic, 1),
        "selected_log_path": str(log_path) if log_path else None,
        "log_lines": stats.log_lines,
        "zone_events": stats.zone_events,
        "dialogue_candidates_heuristic": stats.dialogue_candidates,
        "ocr_attempts": stats.ocr_attempts,
        "ocr_frames_saved": stats.ocr_frames_saved,
        "unique_nonempty_ocr_texts": len(stats.unique_ocr_texts),
        "log_ocr_overlap_candidates": len(overlaps),
        "decision_hint": decision_hint,
        "note": "decision_hint is triage only; inspect raw evidence before locking architecture.",
    }
    write_json(session_dir / "summary.json", summary)

    print("\n============================================================")
    print(" Spike 001 complete")
    print("============================================================")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nEvidence: {session_dir}")
    return session_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="POE2 Spike 001 signal audit")
    parser.add_argument("--seconds", type=int, default=120, help="test duration")
    parser.add_argument("--interval", type=float, default=0.75, help="capture/OCR interval")
    parser.add_argument("--log", type=str, default=None, help="explicit Client.txt path")
    parser.add_argument(
        "--region",
        type=parse_region,
        default=None,
        help="physical pixel capture region: x,y,w,h",
    )
    return parser


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("Spike 001 is Windows-only.")
    asyncio.run(run(build_parser().parse_args()))
