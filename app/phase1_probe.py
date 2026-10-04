from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

from .capture import ScreenCapture
from .dialogue_context import DialogueContextDetector
from .frame_stabilizer import FrameStabilizer
from .ocr_windows import WindowsOcr


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def frame_to_png(frame, path: Path) -> None:
    image = Image.frombytes(
        "RGB",
        (frame.width, frame.height),
        frame.bgra,
        "raw",
        "BGRX",
    )
    image.save(path)


async def run(seconds: int, capture_interval: float) -> Path:
    root = Path(__file__).resolve().parents[1]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session = root / "diagnostics" / "phase1" / stamp
    screenshots = session / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    stats = {
        "captures": 0,
        "visual_changes": 0,
        "ocr_calls": 0,
        "dialogue_detected": 0,
        "normal_right": 0,
        "inventory_left": 0,
        "ocr_errors": 0,
    }

    with ScreenCapture() as capture:
        monitor = capture.primary_monitor()
        region = capture.default_dialogue_region()
        stabilizer = FrameStabilizer()
        ocr = WindowsOcr()
        detector = DialogueContextDetector(region.width, region.height)

        write_json(
            session / "metadata.json",
            {
                "started_at": datetime.now().isoformat(timespec="seconds"),
                "python": sys.version,
                "duration_seconds": seconds,
                "capture_interval_seconds": capture_interval,
                "monitor": monitor,
                "capture_region": region.as_mss(),
                "architecture": "OCR-first",
            },
        )

        print("============================================================")
        print(" POE2 Viet Hoa - Phase 1 Probe")
        print("============================================================")
        print(f"Session: {session}")
        print(f"ROI: {region.as_mss()}")
        print()
        print("Trong luc probe chay:")
        print("- noi chuyen 3-5 cau voi NPC story")
        print("- thu inventory dong va mo neu tien")
        print("- de tool tu chay het thoi gian")
        print()

        deadline = time.monotonic() + seconds
        event_no = 0
        last_change_counted = False

        while time.monotonic() < deadline:
            loop_started = time.monotonic()
            frame = capture.grab(region)
            stats["captures"] += 1

            now = time.monotonic()
            decision = stabilizer.observe(frame.bgra, now=now)

            if decision.dirty_since_ocr and decision.changed_fraction > stabilizer.changed_fraction_threshold:
                if not last_change_counted:
                    stats["visual_changes"] += 1
                    last_change_counted = True
            if decision.reason in {"settled", "max_wait"}:
                last_change_counted = False

            if decision.should_ocr:
                event_no += 1
                try:
                    ocr_result = await ocr.recognize_bgra(
                        frame.bgra,
                        frame.width,
                        frame.height,
                    )
                    stabilizer.mark_ocr()
                    stats["ocr_calls"] += 1

                    context = detector.detect(ocr_result.lines)
                    if context.detected:
                        stats["dialogue_detected"] += 1
                        if context.layout in stats:
                            stats[context.layout] += 1

                    shot_name = f"{event_no:04d}_{datetime.now().strftime('%H%M%S_%f')[:-3]}.png"
                    shot_path = screenshots / shot_name
                    frame_to_png(frame, shot_path)

                    payload = {
                        "event": event_no,
                        "time": datetime.now().isoformat(timespec="milliseconds"),
                        "screenshot": str(shot_path.relative_to(session)),
                        "frame_gate": {
                            "reason": decision.reason,
                            "changed_fraction": round(decision.changed_fraction, 6),
                            "stable_frames": decision.stable_frames,
                        },
                        "ocr": ocr_result.to_dict(),
                        "dialogue": context.to_dict(),
                    }

                    if context.dialogue_box is not None:
                        payload["dialogue"]["global_box"] = context.dialogue_box.translated(
                            region.left,
                            region.top,
                        ).to_dict()

                    append_jsonl(session / "events.jsonl", payload)

                    if context.detected:
                        short = context.text[:110].replace("\n", " ")
                        print(
                            f"[{event_no:02d}] {context.layout:14s} "
                            f"conf={context.confidence:.2f} "
                            f"speaker={context.speaker or '?'} | {short}"
                        )
                    else:
                        print(
                            f"[{event_no:02d}] OCR, no dialogue "
                            f"({', '.join(context.reasons)})"
                        )
                except Exception as exc:
                    # Mark the frame as consumed so one bad frame does not loop OCR
                    # continuously. A new screen change will make it dirty again.
                    stabilizer.mark_ocr()
                    stats["ocr_errors"] += 1
                    append_jsonl(
                        session / "errors.jsonl",
                        {
                            "time": datetime.now().isoformat(timespec="milliseconds"),
                            "type": type(exc).__name__,
                            "message": str(exc),
                        },
                    )
                    print(f"[OCR ERROR] {type(exc).__name__}: {exc}")

            elapsed = time.monotonic() - loop_started
            await asyncio.sleep(max(0.02, capture_interval - elapsed))

    summary = {
        **stats,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "result": "PASS" if stats["dialogue_detected"] > 0 else "NEEDS_REVIEW",
    }
    write_json(session / "summary.json", summary)

    print()
    print("============================================================")
    print(" Phase 1 probe complete")
    print("============================================================")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Evidence: {session}")

    return session


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--interval", type=float, default=0.12)
    args = parser.parse_args()

    if sys.platform != "win32":
        raise SystemExit("Phase 1 probe is Windows-only.")

    asyncio.run(run(max(10, args.seconds), max(0.05, args.interval)))


if __name__ == "__main__":
    main()
