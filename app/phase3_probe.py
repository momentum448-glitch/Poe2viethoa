from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

from .capture import ScreenCapture
from .dialogue_context import DialogueContextDetector
from .dialogue_pipeline import DialogueTranslationPipeline
from .frame_stabilizer import FrameStabilizer
from .game_window import GameWindowProbe
from .matcher import DialogueMatcher
from .ocr_windows import WindowsOcr
from .replacement_overlay import (
    ReplacementOverlay,
    build_overlay_rect,
    enable_per_monitor_dpi_awareness,
    estimate_cover_color,
)
from .translation_store import TranslationStore


FOREGROUND_GRACE_SECONDS = 1.5
FOREGROUND_START_TIMEOUT_SECONDS = 300.0


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


def package_session(root: Path, session: Path) -> Path:
    zip_path = root / f"QC_PHASE3_RESULT_{session.name}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(session.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(session))

    (root / "LAST_QC_RESULT.txt").write_text(
        "FILE CAN GUI CHO CHATGPT:\n" + str(zip_path) + "\n",
        encoding="utf-8",
    )
    return zip_path


def translation_to_dict(result) -> dict[str, Any]:
    if result is None:
        return {"matched": False, "reason": "not_emitted"}

    return {
        "matched": result.matched,
        "confidence": result.confidence,
        "score": result.score,
        "method": result.method,
        "normalized_ocr": result.normalized_ocr,
        "source_id": result.record.id if result.record else None,
        "vi": result.record.vi if result.record else None,
        "candidates": [
            {
                "source_id": c.record.id,
                "score": round(c.score, 2),
                "method": c.method,
            }
            for c in result.candidates
        ],
    }


async def capture_overlay_proof(
    overlay: ReplacementOverlay,
    capture: ScreenCapture,
    region,
    path: Path,
) -> None:
    """Capture one QC-only frame with the overlay visible.

    Runtime capture exclusion stays enabled at all other times. For this proof
    image only, affinity is temporarily disabled and no OCR is run on the frame.
    """

    if not overlay.set_capture_exclusion(False):
        raise RuntimeError("Could not temporarily disable overlay capture exclusion.")

    try:
        overlay.pump()
        await asyncio.sleep(0.08)
        frame = capture.grab(region)
        frame_to_png(frame, path)
    finally:
        if not overlay.set_capture_exclusion(True):
            raise RuntimeError("Could not restore overlay capture exclusion.")


async def run(seconds: int, capture_interval: float, db_path: Path) -> tuple[Path, Path]:
    if sys.platform != "win32":
        raise RuntimeError("Phase 3 probe is Windows-only.")

    enable_per_monitor_dpi_awareness()

    root = Path(__file__).resolve().parents[1]
    if not db_path.exists():
        raise RuntimeError(
            f"Translation DB not found: {db_path}. Run SOURCE_SYNC.bat first."
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session = root / "diagnostics" / "phase3" / stamp
    screenshots = session / "screenshots"
    overlay_proofs = session / "overlay_proofs"
    screenshots.mkdir(parents=True, exist_ok=True)
    overlay_proofs.mkdir(parents=True, exist_ok=True)

    wall_started = time.monotonic()
    active_elapsed = 0.0

    stats = {
        "captures": 0,
        "ocr_calls": 0,
        "dialogue_detected": 0,
        "text_emitted": 0,
        "duplicates_suppressed": 0,
        "matched_high": 0,
        "matched_medium": 0,
        "unmatched": 0,
        "overlay_updates": 0,
        "overlay_clears": 0,
        "overlay_proofs": 0,
        "ocr_errors": 0,
        "overlay_errors": 0,
        "foreground_transient_losses": 0,
        "foreground_pauses": 0,
    }

    store = TranslationStore(db_path)
    overlay: ReplacementOverlay | None = None

    try:
        matcher = DialogueMatcher(store)
        pipeline = DialogueTranslationPipeline(matcher)

        with ScreenCapture() as capture:
            monitor = capture.primary_monitor()
            region = capture.default_dialogue_region()
            stabilizer = FrameStabilizer(max_wait_ms=900)
            ocr = WindowsOcr()
            detector = DialogueContextDetector(region.width, region.height)
            game_window = GameWindowProbe()
            overlay = ReplacementOverlay(monitor)

            if not overlay.capture_exclusion_ok:
                raise RuntimeError(
                    "Windows could not exclude the overlay from screen capture. "
                    "Phase 3 QC stopped to avoid OCR self-capture."
                )

            write_json(
                session / "metadata.json",
                {
                    "started_at": datetime.now().isoformat(timespec="seconds"),
                    "python": sys.version,
                    "duration_seconds": seconds,
                    "capture_interval_seconds": capture_interval,
                    "foreground_grace_seconds": FOREGROUND_GRACE_SECONDS,
                    "duration_policy": "active PoE2 foreground time only",
                    "capture_policy": "overlay excluded from OCR capture",
                    "monitor": monitor,
                    "capture_region": region.as_mss(),
                    "runtime_translation_records": len(matcher.records),
                    "overlay_capture_exclusion": overlay.capture_exclusion_ok,
                    "overlay_mode": "topmost / click-through / replacement mask",
                },
            )

            print("============================================================")
            print(" POE2 Viet Hoa - Phase 3 Replacement Overlay QC")
            print("============================================================")
            print(f"Translations loaded: {len(matcher.records)}")
            print()
            print("Hay mo mot topic Alpha:")
            print("- Renly: Introduction / The Miller")
            print("- Una: Home / Clearfell")
            print()
            print("Khi match High, chu Anh se duoc che va thay bang chu Viet.")
            print("Alt+Tab se tam dung timer va an overlay.")
            print()

            event_no = 0
            game_active = False
            first_game_seen_at: float | None = None
            last_game_seen_at: float | None = None
            pause_announced = False
            no_dialogue_streak = 0
            overlay_visible = False
            current_source_id: str | None = None
            proofed_ids: set[str] = set()

            while active_elapsed < seconds:
                loop_started = time.monotonic()
                now = loop_started
                foreground = game_window.foreground()

                if not foreground.is_poe2:
                    within_grace = (
                        game_active
                        and last_game_seen_at is not None
                        and now - last_game_seen_at <= FOREGROUND_GRACE_SECONDS
                    )

                    if within_grace:
                        stats["foreground_transient_losses"] += 1
                    else:
                        if game_active:
                            stats["foreground_pauses"] += 1
                        game_active = False

                    if overlay_visible and overlay is not None:
                        overlay.clear()
                        overlay_visible = False
                        current_source_id = None
                        stats["overlay_clears"] += 1

                    if not pause_announced:
                        print("[PAUSE] POE2 khong o foreground. Timer/overlay tam dung...")
                        pause_announced = True

                    if (
                        first_game_seen_at is None
                        and time.monotonic() - wall_started >= FOREGROUND_START_TIMEOUT_SECONDS
                    ):
                        raise RuntimeError(
                            "POE2 was not foreground within 300 seconds; Phase 3 QC cancelled."
                        )

                    await asyncio.sleep(max(0.10, capture_interval))
                    continue

                if first_game_seen_at is None:
                    first_game_seen_at = now

                last_game_seen_at = now
                if not game_active:
                    print(f"[GAME] foreground: {foreground.title or foreground.class_name}")
                    stabilizer.reset()
                    pipeline.stabilizer.reset()
                    game_active = True
                    pause_announced = False
                    no_dialogue_streak = 0

                overlay.pump()

                frame = capture.grab(region)
                stats["captures"] += 1
                decision = stabilizer.observe(frame.bgra)

                if decision.should_ocr:
                    event_no += 1
                    raw_path = screenshots / (
                        f"{event_no:04d}_{datetime.now().strftime('%H%M%S_%f')[:-3]}.png"
                    )
                    frame_to_png(frame, raw_path)

                    try:
                        ocr_result = await ocr.recognize_bgra(
                            frame.bgra,
                            frame.width,
                            frame.height,
                        )
                        stabilizer.mark_ocr()
                        stats["ocr_calls"] += 1

                        context = detector.detect(ocr_result.lines)
                        pipeline_decision = None
                        overlay_info = None
                        overlay_action = "keep"

                        if context.detected:
                            no_dialogue_streak = 0
                            stats["dialogue_detected"] += 1
                            pipeline_decision = pipeline.process(
                                context.text,
                                speaker=context.speaker,
                                layout=context.layout,
                            )

                            if pipeline_decision.emit:
                                stats["text_emitted"] += 1
                                result = pipeline_decision.translation

                                if result and result.matched:
                                    if result.confidence == "high":
                                        stats["matched_high"] += 1
                                    elif result.confidence == "medium":
                                        stats["matched_medium"] += 1
                                else:
                                    stats["unmatched"] += 1

                                if (
                                    result
                                    and result.should_display_normal
                                    and result.record is not None
                                    and context.dialogue_box is not None
                                ):
                                    rect = build_overlay_rect(context.dialogue_box, region)
                                    cover = estimate_cover_color(frame, context.dialogue_box)
                                    overlay_info = overlay.show_translation(
                                        rect,
                                        result.record.vi,
                                        cover_color=cover,
                                    )
                                    overlay_visible = True
                                    current_source_id = result.record.id
                                    overlay_action = "show"
                                    stats["overlay_updates"] += 1

                                    if result.record.id not in proofed_ids:
                                        proofed_ids.add(result.record.id)
                                        proof_path = overlay_proofs / (
                                            f"{event_no:04d}_{result.record.id}.png"
                                        )
                                        await capture_overlay_proof(
                                            overlay,
                                            capture,
                                            region,
                                            proof_path,
                                        )
                                        stats["overlay_proofs"] += 1
                                else:
                                    if overlay_visible:
                                        overlay.clear()
                                        overlay_visible = False
                                        current_source_id = None
                                        stats["overlay_clears"] += 1
                                    overlay_action = "hide_unmatched"
                            else:
                                if pipeline_decision.reason == "duplicate":
                                    stats["duplicates_suppressed"] += 1
                                    overlay_action = "keep_duplicate"
                        else:
                            no_dialogue_streak += 1
                            if no_dialogue_streak >= 2 and overlay_visible:
                                overlay.clear()
                                overlay_visible = False
                                current_source_id = None
                                stats["overlay_clears"] += 1
                                overlay_action = "hide_no_dialogue"

                        append_jsonl(
                            session / "events.jsonl",
                            {
                                "event": event_no,
                                "time": datetime.now().isoformat(timespec="milliseconds"),
                                "screenshot": str(raw_path.relative_to(session)),
                                "frame_gate": {
                                    "reason": decision.reason,
                                    "changed_fraction": round(decision.changed_fraction, 6),
                                    "stable_frames": decision.stable_frames,
                                },
                                "dialogue": context.to_dict(),
                                "pipeline": {
                                    "emit": pipeline_decision.emit if pipeline_decision else False,
                                    "reason": (
                                        pipeline_decision.reason
                                        if pipeline_decision
                                        else "not_dialogue"
                                    ),
                                    "translation": translation_to_dict(
                                        pipeline_decision.translation
                                        if pipeline_decision
                                        else None
                                    ),
                                },
                                "overlay": {
                                    "action": overlay_action,
                                    "visible": overlay_visible,
                                    "current_source_id": current_source_id,
                                    "render": (
                                        overlay_info.to_dict()
                                        if overlay_info is not None
                                        else None
                                    ),
                                },
                            },
                        )

                        if context.detected and pipeline_decision:
                            result = pipeline_decision.translation
                            if (
                                pipeline_decision.emit
                                and result
                                and result.should_display_normal
                                and result.record
                            ):
                                print(
                                    f"[OVERLAY {result.score:5.1f}] "
                                    f"{context.speaker or '?'} -> {result.record.vi}"
                                )
                            elif pipeline_decision.emit:
                                print(
                                    f"[NO DISPLAY] {context.speaker or '?'} | "
                                    f"{context.text[:80]}"
                                )

                    except Exception as exc:
                        stabilizer.mark_ocr()
                        if "overlay" in type(exc).__name__.casefold() or "capture exclusion" in str(exc).casefold():
                            stats["overlay_errors"] += 1
                        else:
                            stats["ocr_errors"] += 1

                        append_jsonl(
                            session / "errors.jsonl",
                            {
                                "time": datetime.now().isoformat(timespec="milliseconds"),
                                "type": type(exc).__name__,
                                "message": str(exc),
                            },
                        )
                        print(f"[ERROR] {type(exc).__name__}: {exc}")

                elapsed = time.monotonic() - loop_started
                await asyncio.sleep(max(0.02, capture_interval - elapsed))
                active_elapsed += time.monotonic() - loop_started

    finally:
        if overlay is not None:
            overlay.close()
        store.close()

    result_status = (
        "PASS"
        if stats["matched_high"] > 0
        and stats["overlay_updates"] > 0
        and stats["overlay_proofs"] > 0
        and stats["ocr_errors"] == 0
        and stats["overlay_errors"] == 0
        else "NEEDS_REVIEW"
    )

    summary = {
        **stats,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "active_seconds": round(active_elapsed, 2),
        "elapsed_seconds": round(time.monotonic() - wall_started, 2),
        "result": result_status,
    }
    write_json(session / "summary.json", summary)
    zip_path = package_session(root, session)

    print()
    print("============================================================")
    print(" Phase 3 overlay probe complete")
    print("============================================================")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"ZIP: {zip_path}")

    return session, zip_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--interval", type=float, default=0.12)
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("runtime/translations.sqlite3"),
    )
    args = parser.parse_args()

    if sys.platform != "win32":
        raise SystemExit("Phase 3 probe is Windows-only.")

    asyncio.run(run(max(10, args.seconds), max(0.05, args.interval), args.db))


if __name__ == "__main__":
    main()
