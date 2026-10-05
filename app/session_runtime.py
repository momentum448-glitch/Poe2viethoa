from __future__ import annotations

import asyncio
from contextlib import suppress
import json
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from .capture import ScreenCapture, crop_frame
from .dialogue_context import DialogueContextDetector
from .dialogue_pipeline import DialogueTranslationPipeline
from .dialogue_tracking import absolute_box, position_was_proofed, proof_key, tracking_region
from .frame_stabilizer import FrameStabilizer
from .game_window import ForegroundWindow, GameWindowProbe
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
from .runtime_lock import RuntimeLock
from .version import build_info
from .text_frame_guard import source_text_changed


FOREGROUND_GRACE_SECONDS = 1.5
FOREGROUND_START_TIMEOUT_SECONDS = 300.0
OCR_TIMEOUT_SECONDS = 8.0
ALPHA_EVENT_LOG_LIMIT = 4 * 1024 * 1024
ERROR_LOG_LIMIT = 1024 * 1024


def append_jsonl(path: Path, payload: dict[str, Any], *, max_bytes: int | None = None) -> bool:
    text = json.dumps(payload, ensure_ascii=False) + "\n"
    if max_bytes is not None:
        size = path.stat().st_size if path.exists() else 0
        if size + len(text.encode("utf-8")) > max_bytes:
            return False
    with path.open("a", encoding="utf-8") as f:
        f.write(text)
    return True


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


def package_session(root: Path, session: Path, *, mode: str = "qc") -> Path:
    prefix = "QC_PHASE4_RESULT" if mode == "qc_alpha" else "ALPHA_RESULT" if mode == "alpha" else "QC_PHASE3_RESULT"
    results = root / "results"
    results.mkdir(parents=True, exist_ok=True)
    zip_path = results / f"{prefix}_{session.name}.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(session.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(session))

    pointer = "LAST_ALPHA_RESULT.txt" if mode == "alpha" else "LAST_QC_RESULT.txt"
    (root / pointer).write_text(
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
    *, reference=None, text_box=None, window: ForegroundWindow | None = None,
) -> bool:
    """Capture one QC-only frame with the overlay visible.

    Runtime capture exclusion stays enabled at all other times. For this proof
    image only, affinity is temporarily disabled and no OCR is run on the frame.
    """

    is_current = (lambda: game_window.is_current(window)) if window else game_window.is_game_foreground
    if not is_current():
        return False

    try:
        if not overlay.set_capture_exclusion(False):
            raise OverlayCaptureError("Could not temporarily disable overlay capture exclusion.")
        overlay.pump()
        await asyncio.sleep(0.08)
        if not is_current():
            return False
        frame = capture.grab(region)
        if not is_current():
            return False
        frame_to_png(frame, path)
    finally:
        if not overlay.set_capture_exclusion(True):
            raise OverlayCaptureError("Could not restore overlay capture exclusion.")
    if reference is not None and text_box is not None:
        # Allow DWM to apply the restored exclusion before sampling English.
        overlay.pump()
        await asyncio.sleep(0.04)
        if not is_current():
            path.unlink(missing_ok=True)
            return False
        latest = capture.grab(region)
        if not is_current() or source_text_changed(reference, latest, text_box):
            path.unlink(missing_ok=True)
            return False
    return True


async def recognize_guarded(ocr, frame, *, is_foreground, should_stop, on_foreground_loss):
    """Keep Stop/foreground hiding responsive even while Windows OCR is awaiting."""
    task = asyncio.create_task(ocr.recognize_bgra(frame.bgra, frame.width, frame.height))
    deadline = time.monotonic() + OCR_TIMEOUT_SECONDS
    foreground_lost = False
    try:
        while not task.done():
            if should_stop():
                raise asyncio.CancelledError()
            if not is_foreground():
                foreground_lost = True
                on_foreground_loss()
            if time.monotonic() >= deadline:
                raise TimeoutError("Windows OCR did not complete within 8 seconds.")
            await asyncio.wait({task}, timeout=0.10)
        return await task, foreground_lost
    finally:
        if not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


async def run(
    seconds: float | None,
    capture_interval: float,
    db_path: Path,
    *,
    mode: str = "qc",
    should_stop: Callable[[], bool] | None = None,
    on_status: Callable[[dict[str, Any]], None] | None = None,
    output_root: Path | None = None,
) -> tuple[Path, Path]:
    if sys.platform != "win32":
        raise RuntimeError("Overlay runtime is Windows-only.")

    enable_per_monitor_dpi_awareness()

    if mode not in {"alpha", "qc", "qc_alpha"}:
        raise ValueError("Unknown session mode")
    is_qc = mode != "alpha"
    if is_qc and (seconds is None or seconds <= 0):
        raise ValueError("QC needs a positive active-time duration")
    if not is_qc and seconds is not None:
        raise ValueError("Normal Alpha sessions run until Stop, without a duration")
    should_stop = should_stop or (lambda: False)
    root = output_root or Path(__file__).resolve().parents[1]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder = "alpha" if mode == "alpha" else "phase4" if mode == "qc_alpha" else "phase3"
    session = root / "diagnostics" / folder / stamp
    screenshots = session / "screenshots"
    overlay_proofs = session / "overlay_proofs"
    session.mkdir(parents=True, exist_ok=False)
    if is_qc:
        screenshots.mkdir()
        overlay_proofs.mkdir()

    wall_started = time.monotonic()
    active_elapsed = 0.0

    stats = {
        "captures": 0,
        "discovery_ocr_calls": 0,
        "tracking_ocr_calls": 0,
        "popup_reacquisitions": 0,
        "ocr_calls": 0,
        "dialogue_detected": 0,
        "text_emitted": 0,
        "duplicates_suppressed": 0,
        "matched_high": 0,
        "matched_medium": 0,
        "unmatched": 0,
        "overlay_updates": 0,
        "overlay_clears": 0,
        "stale_text_skips": 0,
        "overlay_proofs": 0,
        "ocr_errors": 0,
        "overlay_errors": 0,
        "runtime_errors": 0,
        "foreground_transient_losses": 0,
        "foreground_pauses": 0,
        "log_entries_dropped": 0,
    }

    last_report_at = -1.0
    last_report_state = ""
    translations_loaded = 0

    def report(state: str, message: str, *, force: bool = False) -> None:
        nonlocal last_report_at, last_report_state
        now = time.monotonic()
        if on_status is None or (not force and state == last_report_state and now - last_report_at < 0.5):
            return
        last_report_at, last_report_state = now, state
        on_status({"state": state, "message": message, "mode": mode,
                   "active_seconds": round(active_elapsed, 1),
                   "duration_seconds": seconds, "stats": dict(stats),
                   "translation_records": translations_loaded, "session": str(session)})

    identity = build_info(root)

    write_json(session / "metadata.json", {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version,
        "duration_seconds": seconds,
        "duration_policy": "active PoE2 foreground time only",
        "capture_policy": "never capture another foreground application",
        "mode": mode,
        "screenshots_enabled": is_qc,
        **identity,
    })
    store: TranslationStore | None = None
    overlay: ReplacementOverlay | None = None
    runtime_lock = RuntimeLock(root / "runtime" / "overlay.lock")
    stop_reason = "completed"
    stage = "setup"
    last_error = ""

    try:
        report("starting", "Đang chuẩn bị OCR và overlay…", force=True)
        runtime_lock.acquire()
        if not db_path.exists():
            raise RuntimeError(f"Translation DB not found: {db_path}. Run SETUP_ALPHA.bat first.")
        store = TranslationStore(db_path)
        matcher = DialogueMatcher(store)
        translations_loaded = len(matcher.records)
        if not translations_loaded:
            raise RuntimeError("Runtime chưa có bản dịch. Hãy chạy SETUP_ALPHA.bat.")
        pipeline = DialogueTranslationPipeline(matcher)

        with ScreenCapture() as capture:
            monitor = capture.desktop_monitor()
            viewport = region = None
            stabilizer = FrameStabilizer(max_wait_ms=900)
            ocr = WindowsOcr()
            known_speakers = {record.speaker for record in matcher.records if record.speaker}
            game_window = GameWindowProbe()
            stage = "overlay"
            overlay = ReplacementOverlay(monitor)

            if not overlay.capture_exclusion_ok:
                raise OverlayCaptureError(
                    "Windows could not exclude the overlay from screen capture. "
                    "QC stopped to avoid OCR self-capture."
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
                    "capture_policy": "foreground game client only; overlay excluded from OCR",
                    "dialogue_position_policy": "full-client discovery, measured popup tracking; reacquire on change",
                    "monitor": monitor,
                    "capture_region": None,
                    "runtime_translation_records": len(matcher.records),
                    "overlay_capture_exclusion": overlay.capture_exclusion_ok,
                    "overlay_mode": "topmost / click-through / replacement mask",
                    "mode": mode,
                    "screenshots_enabled": is_qc,
                    **identity,
                },
            )

            print("============================================================")
            print(" POE2 Viet Hoa - " + ("Local Alpha" if not is_qc else "Overlay QC"))
            print("============================================================")
            print(f"Translations loaded: {len(matcher.records)}")
            print()
            print("Hay mo mot topic Alpha:")
            print("- Act 1: Una / Renly / Finn / The Hooded One")
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
            displayed_frame = None
            displayed_box = None
            proofed_positions: set[tuple[str, int, int]] = set()
            resume_needs_reset = True

            def hide_overlay(*, reset_dedupe: bool = True) -> None:
                nonlocal overlay_visible, current_source_id, displayed_frame, displayed_box
                if overlay_visible:
                    overlay.clear()
                    stats["overlay_clears"] += 1
                overlay_visible = False
                current_source_id = None
                displayed_frame = displayed_box = None
                if reset_dedupe:
                    pipeline.stabilizer.reset()

            def foreground_lost_during_ocr() -> None:
                nonlocal resume_needs_reset
                hide_overlay()
                resume_needs_reset = True
                report("paused", "Tạm dừng — quay lại PoE2 để tiếp tục.")

            while seconds is None or active_elapsed < seconds:
                if should_stop():
                    stop_reason = "stopped"
                    break
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
                    report("paused" if first_game_seen_at is not None else "waiting",
                           "Tạm dừng — quay lại PoE2 để tiếp tục." if first_game_seen_at is not None
                           else "Đang chờ PoE2. Hãy chuyển sang cửa sổ game.")

                    if not pause_announced:
                        print("[PAUSE] POE2 khong o foreground. Timer/overlay tam dung...")
                        pause_announced = True

                    if (
                        is_qc and first_game_seen_at is None
                        and time.monotonic() - wall_started >= FOREGROUND_START_TIMEOUT_SECONDS
                    ):
                        raise RuntimeError(
                            "POE2 was not foreground within 300 seconds; QC cancelled."
                        )

                    await asyncio.sleep(max(0.10, capture_interval))
                    continue

                next_viewport = capture.game_region(foreground.client_region)
                if next_viewport is None:
                    hide_overlay()
                    resume_needs_reset = True
                    report("waiting", "Đang chờ vùng hiển thị PoE2 hợp lệ.")
                    await asyncio.sleep(max(0.10, capture_interval))
                    continue
                if viewport != next_viewport:
                    if viewport is not None:
                        stats["popup_reacquisitions"] += 1
                    hide_overlay()
                    viewport = region = next_viewport
                    stabilizer.reset()

                if first_game_seen_at is None:
                    first_game_seen_at = now
                    metadata_path = session / "metadata.json"
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    metadata["game_window"] = {"class_name": foreground.class_name,
                                               "title": foreground.title}
                    metadata["capture_region"] = viewport.as_mss()
                    write_json(metadata_path, metadata)

                last_game_seen_at = now
                if not game_active or resume_needs_reset:
                    print(f"[GAME] foreground: {foreground.title or foreground.class_name}")
                    stabilizer.reset()
                    pipeline.stabilizer.reset()
                    region = viewport
                    game_active = True
                    pause_announced = False
                    resume_needs_reset = False

                stage = "overlay"
                overlay.pump()
                report("running", "Đang theo dõi hội thoại trong PoE2.")

                # Pumping Tk may dispatch pending events after the first check.
                is_current = lambda: game_window.is_current(foreground)
                if not is_current():
                    hide_overlay()
                    resume_needs_reset = True
                    continue
                stage = "capture"
                frame = capture.grab(region)
                if not is_current():
                    hide_overlay()
                    resume_needs_reset = True
                    continue
                stats["captures"] += 1
                if (overlay_visible and displayed_frame is not None and displayed_box is not None
                        and source_text_changed(displayed_frame, frame, displayed_box)):
                    hide_overlay()
                    stabilizer.reset()
                    stats["stale_text_skips"] += 1
                    if region != viewport:
                        region = viewport
                        stats["popup_reacquisitions"] += 1
                        continue
                # Keep sampled comparison work close to the old small-ROI budget.
                stabilizer.sample_stride = max(8, region.width * region.height // 65000)
                decision = stabilizer.observe(frame.bgra)

                if decision.should_ocr:
                    event_no += 1
                    raw_path = screenshots / (
                        f"{event_no:04d}_{datetime.now().strftime('%H%M%S_%f')[:-3]}.png"
                    )
                    if is_qc:
                        frame_to_png(frame, raw_path)

                    try:
                        stage = "ocr"
                        capture_mode = "discovery" if region == viewport else "tracking"
                        ocr_result, foreground_lost = await recognize_guarded(
                            ocr, frame, is_foreground=is_current,
                            should_stop=should_stop, on_foreground_loss=foreground_lost_during_ocr,
                        )
                        stabilizer.mark_ocr()
                        stats["ocr_calls"] += 1
                        stats[f"{capture_mode}_ocr_calls"] += 1

                        # OCR yields to Windows; never render after an Alt+Tab.
                        if should_stop():
                            raise asyncio.CancelledError()
                        if foreground_lost or not is_current():
                            hide_overlay()
                            resume_needs_reset = True
                            continue

                        stage = "matching"
                        detector = DialogueContextDetector(region.width, region.height,
                                                           known_speakers=known_speakers)
                        context = detector.detect(ocr_result.lines)
                        position = None
                        if context.dialogue_box is not None:
                            screen_box = absolute_box(context.dialogue_box, region)
                            position = (screen_box.x, screen_box.y)
                            # Crop coordinates must not change the dedupe's layout.
                            context.layout = ("inventory_left" if screen_box.cx <
                                              viewport.left + viewport.width * 0.48 else "normal_right")
                            context.reasons = [reason for reason in context.reasons
                                               if not reason.startswith("layout=")] + [f"layout={context.layout}"]
                        pipeline_decision = None
                        overlay_info = None
                        overlay_action = "keep"
                        proof_relative_path = None

                        stale_during_ocr = False
                        if context.detected and context.dialogue_box is not None:
                            latest = capture.grab(region)
                            if not is_current():
                                hide_overlay()
                                resume_needs_reset = True
                                continue
                            stale_during_ocr = source_text_changed(frame, latest, context.dialogue_box)
                        if stale_during_ocr:
                            hide_overlay()
                            stabilizer.reset()
                            stats["stale_text_skips"] += 1
                            overlay_action = "hide_changed_text"
                        elif context.detected:
                            stats["dialogue_detected"] += 1
                            pipeline_decision = pipeline.process(
                                context.text,
                                speaker=context.speaker,
                                layout=context.layout,
                                position=position,
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
                                    rect = build_overlay_rect(context.dialogue_box, region,
                                                              continue_box=context.continue_box)
                                    cover = estimate_cover_color(frame, context.dialogue_box)
                                    overlay_info = overlay.show_translation(
                                        rect,
                                        result.record.vi,
                                        cover_color=cover,
                                    )
                                    overlay_visible = True
                                    displayed_frame, displayed_box = frame, context.dialogue_box
                                    current_source_id = result.record.id
                                    overlay_action = "show"
                                    stats["overlay_updates"] += 1

                                    key = proof_key(result.record.id, context.dialogue_box, region)
                                    if is_qc and not position_was_proofed(key, proofed_positions):
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
                                            reference=frame, text_box=context.dialogue_box,
                                            window=foreground,
                                        )
                                        if proof_captured:
                                            proofed_positions.add(key)
                                            stats["overlay_proofs"] += 1
                                            proof_relative_path = proof_path.relative_to(session).as_posix()
                                        else:
                                            hide_overlay()
                                            resume_needs_reset = True
                                            overlay_action = "hide_stale_or_foreground"
                                            stats["stale_text_skips"] += 1
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
                        logged = append_jsonl(
                            session / "events.jsonl",
                            {
                                "event": event_no,
                                "time": datetime.now().isoformat(timespec="milliseconds"),
                                "screenshot": str(raw_path.relative_to(session)) if is_qc else None,
                                "capture_region": region.as_mss(),
                                "capture_mode": capture_mode,
                                "ocr": ocr_result.to_dict() if is_qc else None,
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
                                        else "source_changed_during_ocr" if stale_during_ocr else "not_dialogue"
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
                                    "proof": proof_relative_path,
                                    "render": (
                                        overlay_info.to_dict()
                                        if overlay_info is not None
                                        else None
                                    ),
                                },
                            },
                            max_bytes=None if is_qc else ALPHA_EVENT_LOG_LIMIT,
                        )
                        if not logged:
                            stats["log_entries_dropped"] += 1

                        if overlay_visible and displayed_frame is not None and region == viewport:
                            next_region = tracking_region(context, region, viewport)
                            if next_region != region:
                                displayed_frame = crop_frame(displayed_frame, next_region)
                                displayed_box = displayed_box.translated(region.left - next_region.left,
                                                                         region.top - next_region.top)
                                region = next_region
                                stabilizer.reset()
                        elif not overlay_visible and region != viewport:
                            region = viewport
                            stabilizer.reset()
                            stats["popup_reacquisitions"] += 1

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
                        last_error = str(exc)
                        stabilizer.mark_ocr()
                        if stage in {"overlay", "proof"}:
                            stats["overlay_errors"] += 1
                        elif stage == "ocr":
                            stats["ocr_errors"] += 1
                        else:
                            stats["runtime_errors"] += 1
                        hide_overlay()
                        region = viewport
                        stabilizer.reset()

                        append_jsonl(
                            session / "errors.jsonl",
                            {
                                "time": datetime.now().isoformat(timespec="milliseconds"),
                                "type": type(exc).__name__,
                                "message": str(exc),
                                "stage": stage,
                            },
                            max_bytes=ERROR_LOG_LIMIT,
                        )
                        report("running", "Có lỗi xử lý; xem chẩn đoán khi dừng.", force=True)
                        print(f"[ERROR] {type(exc).__name__}: {exc}")

                elapsed = time.monotonic() - loop_started
                remaining = float("inf") if seconds is None else seconds - active_elapsed
                await asyncio.sleep(max(0.0, min(remaining, capture_interval - elapsed)))
                if game_window.is_game_foreground():
                    active_elapsed = min(float("inf") if seconds is None else seconds,
                                         active_elapsed + time.monotonic() - loop_started)
                else:
                    hide_overlay()
                    resume_needs_reset = True

    except (asyncio.CancelledError, KeyboardInterrupt):
        stop_reason = "stopped" if should_stop() else "interrupted"
        print("[STOP] Dang dong goi ket qua da thu...")
    except Exception as exc:
        last_error = str(exc)
        stop_reason = "error"
        stats["overlay_errors" if stage in {"overlay", "proof"} else "runtime_errors"] += 1
        append_jsonl(session / "errors.jsonl", {
            "time": datetime.now().isoformat(timespec="milliseconds"),
            "type": type(exc).__name__, "message": str(exc), "stage": stage,
            "fatal": True,
        }, max_bytes=ERROR_LOG_LIMIT)
        report("error", str(exc), force=True)
        print(f"[ERROR] {type(exc).__name__}: {exc}")
    finally:
        for resource in (overlay, store, runtime_lock):
            if resource is not None:
                try:
                    resource.close()
                except Exception as exc:
                    stats["runtime_errors"] += 1
                    stop_reason = "error"
                    append_jsonl(session / "errors.jsonl", {
                        "type": type(exc).__name__, "message": str(exc),
                        "stage": "cleanup", "fatal": True,
                    }, max_bytes=ERROR_LOG_LIMIT)

    result_status = (
        "TECHNICAL_PASS"
        if is_qc and stats["matched_high"] > 0
        and stats["overlay_updates"] > 0
        and stats["overlay_proofs"] > 0
        and stats["ocr_errors"] == 0
        and stats["overlay_errors"] == 0
        and stats["runtime_errors"] == 0
        and stop_reason == "completed"
        and seconds is not None and active_elapsed >= seconds
        else "NEEDS_REVIEW"
    )
    if not is_qc and stop_reason == "stopped":
        result_status = "NEEDS_REVIEW" if any(stats[k] for k in ("ocr_errors", "overlay_errors", "runtime_errors")) else "STOPPED"
    elif stop_reason != "completed":
        result_status = "INTERRUPTED" if stop_reason in {"interrupted", "stopped"} else "ERROR"

    summary = {
        **stats,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "active_seconds": round(active_elapsed, 2),
        "elapsed_seconds": round(time.monotonic() - wall_started, 2),
        "result": result_status,
        "stop_reason": stop_reason,
        "visual_qc_required": is_qc,
        "mode": mode,
        "last_error": last_error or None,
        **identity,
    }
    write_json(session / "summary.json", summary)
    zip_path = package_session(root, session, mode=mode)

    print()
    print("============================================================")
    print(" Overlay session complete")
    print("============================================================")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"ZIP: {zip_path}")

    return session, zip_path
