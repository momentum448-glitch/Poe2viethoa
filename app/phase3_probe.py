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
    OverlayCaptureError,
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
    game_window: GameWindowProbe,
) -> bool:
    """Capture one QC-only frame with the overlay visible.

    Runtime capture exclusion stays enabled at all other times. For this proof
    image only, affinity is temporarily disabled and no OCR is run on the frame.
    """

    if not game_window.is_game_foreground():
        return False

    try:
        if not overlay.set_capture_exclusion(False):
            raise OverlayCaptureError("Could not temporarily disable overlay capture exclusion.")
        overlay.pump()
        await asyncio.sleep(0.08)
        if not game_window.is_game_foreground():
            return False
        frame = capture.grab(region)
        if not game_window.is_game_foreground():
            return False
        frame_to_png(frame, path)
        return True
    finally:
        if not overlay.set_capture_exclusion(True):
            raise OverlayCaptureError("Could not restore overlay capture exclusion.")


async def run(seconds: int, capture_interval: float, db_path: Path) -> tuple[Path, Path]:
    if sys.platform != "win32":
        raise RuntimeError("Phase 3 probe is Windows-only.")

    enable_per_monitor_dpi_awareness()

    root = Path(__file__).resolve().parents[1]
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
        "runtime_errors": 0,
        "foreground_transient_losses": 0,
        "foreground_pauses": 0,
    }

    write_json(session / "metadata.json", {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version,
        "duration_seconds": seconds,
        "duration_policy": "active PoE2 foreground time only",
        "capture_policy": "never capture another foreground application",
    })
    store: TranslationStore | None = None
    overlay: ReplacementOverlay | None = None
    stop_reason = "completed"
    stage = "setup"

    try:
        if not db_path.exists():
            raise RuntimeError(f"Translation DB not found: {db_path}. Run SOURCE_SYNC.bat first.")
        store = TranslationStore(db_path)
        matcher = DialogueMatcher(store)
        pipeline = DialogueTranslationPipeline(matcher)

        with ScreenCapture() as capture:
            monitor = capture.primary_monitor()
            region = capture.default_dialogue_region()
            stabilizer = FrameStabilizer(max_wait_ms=900)
            ocr = WindowsOcr()
            detector = DialogueContextDetector(region.width, region.height)
            game_window = GameWindowProbe()
            stage = "overlay"
            overlay = ReplacementOverlay(monitor)

            if not overlay.capture_exclusion_ok:
                raise OverlayCaptureError(
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
            overlay_visible = False
            current_source_id: str | None = None
            proofed_ids: set[str] = set()
            resume_needs_reset = True

            def hide_overlay(*, reset_dedupe: bool = True) -> None:
                nonlocal overlay_visible, current_source_id
                if overlay_visible:
                    overlay.clear()
                    stats["overlay_clears"] += 1
                overlay_visible = False
                current_source_id = None
                if reset_dedupe:
                    pipeline.stabilizer.reset()

            while active_elapsed < seconds:
                loop_started = time.monotonic()
                now = loop_started
                stage = "foreground"
                foreground = game_window.foreground()

                if not foreground.is_poe2:
                    resume_needs_reset = True
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

                    hide_overlay()

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
                if not game_active or resume_needs_reset:
                    print(f"[GAME] foreground: {foreground.title or foreground.class_name}")
                    stabilizer.reset()
                    pipeline.stabilizer.reset()
                    game_active = True
                    pause_announced = False
                    resume_needs_reset = False

                stage = "overlay"
                overlay.pump()

                # Pumping Tk may dispatch pending events after the first check.
                if not game_window.is_game_foreground():
                    hide_overlay()
                    resume_needs_reset = True
                    continue
                stage = "capture"
                frame = capture.grab(region)
                if not game_window.is_game_foreground():
                    hide_overlay()
                    resume_needs_reset = True
                    continue
                stats["captures"] += 1
                decision = stabilizer.observe(frame.bgra)

                if decision.should_ocr:
                    event_no += 1
                    raw_path = screenshots / (
                        f"{event_no:04d}_{datetime.now().strftime('%H%M%S_%f')[:-3]}.png"
                    )
                    frame_to_png(frame, raw_path)

                    try:
                        stage = "ocr"
                        ocr_result = await ocr.recognize_bgra(
                            frame.bgra,
                            frame.width,
                            frame.height,
                        )
                        stabilizer.mark_ocr()
                        stats["ocr_calls"] += 1

                        # OCR yields to Windows; never render after an Alt+Tab.
                        if not game_window.is_game_foreground():
                            hide_overlay()
                            resume_needs_reset = True
                            continue

                        stage = "matching"
                        context = detector.detect(ocr_result.lines)
                        pipeline_decision = None
                        overlay_info = None
                        overlay_action = "keep"

                        if context.detected:
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
                                    stage = "overlay"
                                    continue_boxes = [
                                        line.box for line in ocr_result.lines
                                        if line.box is not None
                                        and line.text.strip().casefold() == "continue"
                                        and line.box.y >= context.dialogue_box.bottom
                                        and abs(line.box.cx - context.dialogue_box.cx) < context.dialogue_box.w
                                    ]
                                    continue_box = min(continue_boxes, key=lambda box: box.y, default=None)
                                    rect = build_overlay_rect(context.dialogue_box, region, continue_box=continue_box)
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
                                        stage = "proof"
                                        proof_path = overlay_proofs / (
                                            f"{event_no:04d}_{result.record.id}.png"
                                        )
                                        proof_captured = await capture_overlay_proof(
                                            overlay,
                                            capture,
                                            region,
                                            proof_path,
                                            game_window,
                                        )
                                        if proof_captured:
                                            proofed_ids.add(result.record.id)
                                            stats["overlay_proofs"] += 1
                                        else:
                                            hide_overlay()
                                            resume_needs_reset = True
                                            overlay_action = "hide_foreground"
                                            overlay_info = None
                                else:
                                    stage = "overlay"
                                    hide_overlay(reset_dedupe=False)
                                    overlay_action = "hide_unmatched"
                            else:
                                if pipeline_decision.reason == "duplicate":
                                    stats["duplicates_suppressed"] += 1
                                    overlay_action = "keep_duplicate"
                        else:
                            # A static menu may never trigger a second OCR call.
                            stage = "overlay"
                            hide_overlay()
                            overlay_action = "hide_no_dialogue"

                        stage = "logging"
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

                    except OverlayCaptureError:
                        # Continuing would risk reading the overlay back into OCR.
                        raise
                    except Exception as exc:
                        stabilizer.mark_ocr()
                        if stage in {"overlay", "proof"}:
                            stats["overlay_errors"] += 1
                        elif stage == "ocr":
                            stats["ocr_errors"] += 1
                        else:
                            stats["runtime_errors"] += 1
                        hide_overlay()

                        append_jsonl(
                            session / "errors.jsonl",
                            {
                                "time": datetime.now().isoformat(timespec="milliseconds"),
                                "type": type(exc).__name__,
                                "message": str(exc),
                                "stage": stage,
                            },
                        )
                        print(f"[ERROR] {type(exc).__name__}: {exc}")

                elapsed = time.monotonic() - loop_started
                await asyncio.sleep(max(0.0, min(seconds - active_elapsed, capture_interval - elapsed)))
                if game_window.is_game_foreground():
                    active_elapsed = min(seconds, active_elapsed + time.monotonic() - loop_started)
                else:
                    hide_overlay()
                    resume_needs_reset = True

    except (asyncio.CancelledError, KeyboardInterrupt):
        stop_reason = "interrupted"
        print("[STOP] QC dung som. Dang dong goi ket qua da thu...")
    except Exception as exc:
        stop_reason = "error"
        stats["overlay_errors" if stage in {"overlay", "proof"} else "runtime_errors"] += 1
        append_jsonl(session / "errors.jsonl", {
            "time": datetime.now().isoformat(timespec="milliseconds"),
            "type": type(exc).__name__, "message": str(exc), "stage": stage,
            "fatal": True,
        })
        print(f"[ERROR] {type(exc).__name__}: {exc}")
    finally:
        for resource in (overlay, store):
            if resource is not None:
                try:
                    resource.close()
                except Exception as exc:
                    stats["runtime_errors"] += 1
                    stop_reason = "error"
                    append_jsonl(session / "errors.jsonl", {
                        "type": type(exc).__name__, "message": str(exc),
                        "stage": "cleanup", "fatal": True,
                    })

    result_status = (
        "TECHNICAL_PASS"
        if stats["matched_high"] > 0
        and stats["overlay_updates"] > 0
        and stats["overlay_proofs"] > 0
        and stats["ocr_errors"] == 0
        and stats["overlay_errors"] == 0
        and stats["runtime_errors"] == 0
        and stop_reason == "completed"
        and active_elapsed >= seconds
        else "NEEDS_REVIEW"
    )
    if stop_reason != "completed":
        result_status = "INTERRUPTED" if stop_reason == "interrupted" else "ERROR"

    summary = {
        **stats,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "active_seconds": round(active_elapsed, 2),
        "elapsed_seconds": round(time.monotonic() - wall_started, 2),
        "result": result_status,
        "stop_reason": stop_reason,
        "visual_qc_required": True,
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

    session, _ = asyncio.run(run(max(10, args.seconds), max(0.05, args.interval), args.db))
    result = json.loads((session / "summary.json").read_text(encoding="utf-8"))["result"]
    if result in {"ERROR", "INTERRUPTED"}:
        raise SystemExit(130 if result == "INTERRUPTED" else 1)


if __name__ == "__main__":
    main()
