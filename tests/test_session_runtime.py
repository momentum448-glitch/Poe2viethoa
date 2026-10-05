import asyncio
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from zipfile import ZipFile

from PIL import Image, ImageDraw

from app import session_runtime as probe
from app.capture import CaptureRegion, CapturedFrame
from app.dialogue_context import DialogueContextDetector as RealContextDetector
from app.frame_stabilizer import StabilizerDecision
from app.game_window import ForegroundWindow
from app.models import DialogueContext, OcrLine, OcrResult, Rect
from app.replacement_overlay import OverlayCaptureError, OverlayRenderInfo
from app.translation_models import TranslationRecord
from app.translation_store import build_sqlite


TEXT = "The old bridge has fallen."
CONTEXT = DialogueContext(True, "normal_right", 0.99, "Keeper", TEXT, Rect(10, 4, 35, 8))
NO_DIALOGUE = DialogueContext(False, "unknown", 0.0, None, "", None)


class SessionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "translations.sqlite3"
        build_sqlite([TranslationRecord("dlg_test", TEXT, "Cây cầu cũ đã sập.",
                                       speaker="Keeper", status="approved")], self.db)
        self.region = CaptureRegion(0, 0, 64, 32)
        self.frame = CapturedFrame(b"\x10\x10\x10\xff" * 2048, 64, 32, self.region)
        self.clock = SimpleNamespace(now=0.0)
        self.is_game = lambda: True
        self.overlay = Mock(capture_exclusion_ok=True)
        self.overlay.set_capture_exclusion.return_value = True
        self.overlay.show_translation.side_effect = lambda rect, text, **kwargs: OverlayRenderInfo(
            rect, 12, (text,), kwargs["cover_color"],
        )
        self.capture = Mock()
        self.capture.__enter__ = Mock(return_value=self.capture)
        self.capture.__exit__ = Mock(return_value=False)
        self.capture.desktop_monitor.return_value = {"left": 0, "top": 0, "width": 64, "height": 32}
        self.capture.game_region.side_effect = lambda client: client
        self.game_region = self.region
        self.capture.grab.side_effect = self.grab
        self.ocr = Mock()
        self.ocr.recognize_bgra = AsyncMock(return_value=OcrResult(TEXT, [], 1.0))
        self.detector = Mock()
        self.detector.detect.return_value = CONTEXT
        self.stabilizer = Mock()
        self.stabilizer.observe.return_value = StabilizerDecision(True, 1.0, 2, True, "settled")
        self.game_window = Mock()
        self.game_window.is_game_foreground.side_effect = lambda: self.is_game()
        self.game_window.foreground.side_effect = lambda: ForegroundWindow(
            1, "Path of Exile 2" if self.is_game() else "Other app",
            "POEWindowClass" if self.is_game() else "OtherApp", self.game_region,
        )

        self.game_window.is_current.side_effect = lambda expected: (
            self.is_game() and self.game_region == expected.client_region)

    def grab(self, region):
        self.assertTrue(self.is_game(), "Capture must never run over another foreground app")
        return probe.crop_frame(self.frame, region)

    async def sleep(self, seconds):
        self.clock.now += max(0.001, seconds)

    def run_probe(self, *, seconds=0.35, db=None, overlay_error=None, **options):
        replacements = {
            "__file__": str(self.root / "app" / "session_runtime.py"),
            "enable_per_monitor_dpi_awareness": Mock(),
            "ScreenCapture": Mock(return_value=self.capture),
            "FrameStabilizer": Mock(return_value=self.stabilizer),
            "WindowsOcr": Mock(return_value=self.ocr),
            "DialogueContextDetector": Mock(return_value=self.detector),
            "GameWindowProbe": Mock(return_value=self.game_window),
            "ReplacementOverlay": Mock(return_value=self.overlay, side_effect=overlay_error),
        }
        with ExitStack() as stack:
            for name, replacement in replacements.items():
                stack.enter_context(patch.object(probe, name, replacement))
            stack.enter_context(patch.object(probe.sys, "platform", "win32"))
            stack.enter_context(patch.object(probe.time, "monotonic", lambda: self.clock.now))
            stack.enter_context(patch.object(probe.asyncio, "sleep", self.sleep))
            stack.enter_context(redirect_stdout(io.StringIO()))
            session, archive = asyncio.run(probe.run(seconds, 0.12, db or self.db, **options))
        summary = json.loads((session / "summary.json").read_text(encoding="utf-8"))
        return session, archive, summary

    def moving_scene(self, position_at):
        self.region = self.game_region = CaptureRegion(180, 60, 1280, 720)
        self.capture.desktop_monitor.return_value = {"left": -1920, "top": 0, "width": 3840, "height": 1080}
        self.last_region = self.region
        self.ocr_size = (1280, 720)

        def grab(region):
            self.assertTrue(self.is_game())
            viewport = self.game_region
            image = Image.new("RGB", (viewport.width, viewport.height), (16, 16, 16))
            x, y = position_at(self.clock.now)
            ImageDraw.Draw(image).rectangle((x + 3, y + 52, x + 90, y + 64), fill=(238, 228, 201))
            self.last_region = region
            frame = CapturedFrame(image.tobytes("raw", "BGRX"), viewport.width, viewport.height, viewport)
            return probe.crop_frame(frame, region)

        async def recognize(bgra, width, height):
            self.ocr_size = (width, height)
            x, y = position_at(self.clock.now)
            x += self.game_region.left - self.last_region.left
            y += self.game_region.top - self.last_region.top
            lines = [OcrLine("Keeper", Rect(x + 75, y, 70, 22)),
                     OcrLine(TEXT, Rect(x, y + 48, 200, 20)),
                     OcrLine("Continue", Rect(x + 60, y + 140, 80, 20))]
            return OcrResult(TEXT, lines, 1.0)

        self.capture.grab.side_effect = grab
        self.ocr.recognize_bgra.side_effect = recognize
        self.detector.detect.side_effect = lambda lines: RealContextDetector(
            *self.ocr_size, known_speakers={"Keeper"}).detect(lines)
        return recognize

    def test_discovery_then_tracking_preserves_absolute_position_and_reference(self):
        self.moving_scene(lambda now: (780, 100))
        session, _, summary = self.run_probe(seconds=0.70)
        self.assertEqual(summary["result"], "TECHNICAL_PASS")
        self.assertEqual(self.overlay.show_translation.call_count, 1)
        self.assertEqual(summary["stale_text_skips"], 0)
        self.assertGreater(summary["tracking_ocr_calls"], 0)
        events = [json.loads(line) for line in (session / "events.jsonl").read_text().splitlines()]
        self.assertEqual(events[0]["capture_region"], self.region.as_mss())
        for event in events:
            box, region = event["dialogue"]["dialogue_box"], event["capture_region"]
            self.assertEqual((region["left"] + box["x"], region["top"] + box["y"]), (960, 208))
            self.assertEqual(event["dialogue"]["layout"], "normal_right")
            self.assertTrue(event["ocr"]["lines"])

    def test_same_page_in_a_new_corner_reacquires_and_creates_a_second_proof(self):
        self.moving_scene(lambda now: (780, 100) if now < .23 else (1010, 460))
        session, _, summary = self.run_probe(seconds=0.70)
        self.assertEqual(summary["result"], "TECHNICAL_PASS")
        self.assertEqual(self.overlay.show_translation.call_count, 2)
        self.assertEqual(summary["overlay_proofs"], 2)
        self.assertGreaterEqual(summary["popup_reacquisitions"], 1)
        self.assertGreaterEqual(self.overlay.clear.call_count, 1)
        events = [json.loads(line) for line in (session / "events.jsonl").read_text().splitlines()]
        shows = [e for e in events if e["overlay"]["action"] == "show"]
        self.assertEqual([e["overlay"]["current_source_id"] for e in shows], ["dlg_test", "dlg_test"])
        self.assertTrue(all(e["overlay"]["proof"] for e in shows))
        self.assertGreater(shows[1]["overlay"]["render"]["rect"]["top"],
                           shows[0]["overlay"]["render"]["rect"]["top"] + 300)

    def test_window_move_during_ocr_discards_old_coordinates_before_rendering(self):
        recognize = self.moving_scene(lambda now: (780, 100))
        first = True

        async def move(bgra, width, height):
            nonlocal first
            result = await recognize(bgra, width, height)
            if first:
                first = False
                self.game_region = CaptureRegion(300, 60, 1280, 720)
            return result

        self.ocr.recognize_bgra.side_effect = move
        _, _, summary = self.run_probe(seconds=.70)
        self.assertEqual(summary["result"], "TECHNICAL_PASS")
        self.assertEqual(self.overlay.show_translation.call_count, 1)
        rect = self.overlay.show_translation.call_args.args[0]
        self.assertEqual(rect.left, 300 + 780 - 18)

    def test_native_game_with_unavailable_client_bounds_waits_without_capturing(self):
        self.game_region = None
        _, _, summary = self.run_probe(seconds=None, mode="alpha", should_stop=lambda: self.clock.now > .2)
        self.assertEqual(summary["result"], "STOPPED")
        self.capture.grab.assert_not_called()
        self.overlay.show_translation.assert_not_called()

    def test_fast_alt_tab_restores_the_same_translation_before_dedupe_timeout(self):
        self.is_game = lambda: not (0.115 <= self.clock.now < 0.235)
        _, _, summary = self.run_probe()
        self.assertGreaterEqual(self.overlay.show_translation.call_count, 2)
        self.assertGreaterEqual(self.overlay.clear.call_count, 1)
        self.assertEqual(summary["result"], "TECHNICAL_PASS")
        self.assertEqual(summary["active_seconds"], 0.35)

    def test_closing_and_reopening_the_same_dialogue_restores_the_overlay(self):
        contexts = iter([CONTEXT, NO_DIALOGUE, CONTEXT])
        self.detector.detect.side_effect = lambda lines: next(contexts, CONTEXT)
        self.run_probe(seconds=0.60)
        self.assertGreaterEqual(self.overlay.show_translation.call_count, 2)
        self.assertTrue(self.overlay.clear.called)

    def painted_frame(self, *, changed=False):
        image = Image.new("RGB", (64, 32), (16, 16, 16))
        ImageDraw.Draw(image).rectangle((12 if not changed else 32, 5, 25 if not changed else 44, 10),
                                        fill=(238, 228, 201))
        return CapturedFrame(image.tobytes("raw", "BGRX"), 64, 32, self.region)

    def test_page_changed_while_ocr_was_pending_never_displays_old_translation(self):
        self.frame = self.painted_frame()

        async def recognize(*args):
            self.frame = self.painted_frame(changed=True)
            return OcrResult(TEXT, [], 1.0)

        self.ocr.recognize_bgra.side_effect = recognize
        session, _, summary = self.run_probe(seconds=0.05)
        self.overlay.show_translation.assert_not_called()
        self.assertEqual(summary["stale_text_skips"], 1)
        event = json.loads((session / "events.jsonl").read_text())
        self.assertEqual(event["pipeline"]["reason"], "source_changed_during_ocr")

    def test_page_changed_during_proof_discards_proof_and_hides_overlay(self):
        self.frame = self.painted_frame()
        original_grab = self.grab
        count = 0

        def grab(region):
            nonlocal count
            count += 1
            if count == 4:  # raw, OCR guard, visible proof, excluded verification
                self.frame = self.painted_frame(changed=True)
            return original_grab(region)

        self.capture.grab.side_effect = grab
        session, _, summary = self.run_probe(seconds=0.05)
        self.assertEqual(summary["overlay_proofs"], 0)
        self.assertEqual(summary["stale_text_skips"], 1)
        self.assertTrue(self.overlay.clear.called)
        self.assertEqual(list((session / "overlay_proofs").iterdir()), [])

    def test_setup_failure_still_produces_a_zip_with_error_and_summary(self):
        _, archive, summary = self.run_probe(overlay_error=OverlayCaptureError("affinity failed"))
        self.assertEqual(summary["result"], "ERROR")
        with ZipFile(archive) as z:
            self.assertTrue({"metadata.json", "summary.json", "errors.jsonl"} <= set(z.namelist()))
        self.assertTrue((self.root / "LAST_QC_RESULT.txt").exists())

    def test_missing_database_is_packaged_instead_of_losing_diagnostics(self):
        _, archive, summary = self.run_probe(db=self.root / "missing.sqlite3")
        self.assertTrue(archive.exists())
        self.assertEqual(summary["stop_reason"], "error")

    def test_interrupted_ocr_still_closes_overlay_and_packages_partial_results(self):
        self.ocr.recognize_bgra.side_effect = asyncio.CancelledError()
        _, archive, summary = self.run_probe()
        self.assertEqual(summary["result"], "INTERRUPTED")
        self.assertTrue(self.overlay.close.called)
        with ZipFile(archive) as z:
            self.assertIn("summary.json", z.namelist())
            self.assertTrue(any(name.startswith("screenshots/") for name in z.namelist()))

    def test_failed_affinity_restore_stops_capture_and_packages_the_failure(self):
        self.overlay.set_capture_exclusion.side_effect = [True, False]
        _, archive, summary = self.run_probe()
        self.assertEqual(summary["result"], "ERROR")
        self.assertEqual(summary["overlay_errors"], 1)
        self.assertEqual(self.capture.grab.call_count, 3)  # raw + current-source guard + proof
        self.assertTrue(archive.exists())

    def test_ocr_error_clears_previous_translation_and_can_recover(self):
        outcomes = iter([OcrResult(TEXT, [], 1.0), RuntimeError("OCR failed")])

        async def recognize(*args):
            outcome = next(outcomes, OcrResult(TEXT, [], 1.0))
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        self.ocr.recognize_bgra.side_effect = recognize
        _, _, summary = self.run_probe(seconds=0.60)
        self.assertEqual(summary["ocr_errors"], 1)
        self.assertEqual(summary["result"], "NEEDS_REVIEW")
        self.assertTrue(self.overlay.clear.called)
        self.assertGreaterEqual(self.overlay.show_translation.call_count, 2)

    def test_capture_failure_still_closes_overlay_and_produces_zip(self):
        self.capture.grab.side_effect = RuntimeError("MSS capture failed")
        _, archive, summary = self.run_probe()
        self.assertEqual(summary["result"], "ERROR")
        self.assertTrue(self.overlay.close.called)
        self.assertTrue(archive.exists())

    def test_untranslated_dialogue_remains_hidden_and_is_still_deduplicated(self):
        self.detector.detect.return_value = DialogueContext(
            True, "normal_right", 0.99, "Keeper", "A completely different story without a translation.", Rect(10, 4, 35, 8),
        )
        _, _, summary = self.run_probe()
        self.assertEqual(summary["unmatched"], 1)
        self.assertGreater(summary["duplicates_suppressed"], 0)
        self.assertFalse(self.overlay.show_translation.called)

    def test_alt_tab_during_ocr_does_not_render_over_another_app(self):
        foreground = [True]
        self.is_game = lambda: foreground[0]
        calls = [0]

        async def recognize(*args):
            calls[0] += 1
            if calls[0] == 1:
                foreground[0] = False
            return OcrResult(TEXT, [], 1.0)

        async def resume_after_sleep(seconds):
            self.clock.now += max(0.001, seconds)
            foreground[0] = True

        def show(rect, text, **kwargs):
            self.assertTrue(foreground[0])
            return OverlayRenderInfo(rect, 12, (text,), kwargs["cover_color"])

        self.sleep = resume_after_sleep
        self.ocr.recognize_bgra.side_effect = recognize
        self.overlay.show_translation.side_effect = show
        _, _, summary = self.run_probe()
        self.assertGreater(calls[0], 1)
        self.assertEqual(summary["result"], "TECHNICAL_PASS")

    def test_alpha_runs_until_stop_without_images_or_affinity_toggling(self):
        reports = []
        session, archive, summary = self.run_probe(
            seconds=None, mode="alpha", should_stop=lambda: self.clock.now >= 1.0,
            on_status=reports.append,
        )
        self.assertEqual(summary["result"], "STOPPED")
        self.assertGreaterEqual(summary["active_seconds"], 1.0)
        self.assertGreater(summary["overlay_updates"], 0)
        self.assertFalse((session / "screenshots").exists())
        self.assertFalse(self.overlay.set_capture_exclusion.called)
        self.assertTrue(archive.name.startswith("ALPHA_RESULT_"))
        with ZipFile(archive) as z:
            self.assertTrue({"metadata.json", "summary.json", "events.jsonl"} <= set(z.namelist()))
            self.assertFalse(any(name.endswith(".png") for name in z.namelist()))
        self.assertTrue((self.root / "LAST_ALPHA_RESULT.txt").exists())
        self.assertTrue(any(r["state"] == "running" for r in reports))

    def test_alpha_can_wait_more_than_300_seconds_for_game_and_still_stop(self):
        self.is_game = lambda: False

        async def long_wait(seconds):
            self.clock.now += 60.0

        self.sleep = long_wait
        _, _, summary = self.run_probe(seconds=None, mode="alpha",
                                       should_stop=lambda: self.clock.now >= 360.0)
        self.assertEqual(summary["result"], "STOPPED")
        self.assertEqual(summary["active_seconds"], 0)
        self.assertEqual(self.capture.grab.call_count, 0)

    def test_stop_during_pending_ocr_cancels_it_and_closes_overlay(self):
        stop = [False]
        cancelled = [False]

        async def pending(*args):
            stop[0] = True
            # Advance the fixture clock so asyncio's polling timeout can fire.
            self.clock.now += 0.2
            try:
                await asyncio.Future()
            finally:
                cancelled[0] = True

        self.ocr.recognize_bgra.side_effect = pending
        _, archive, summary = self.run_probe(seconds=None, mode="alpha", should_stop=lambda: stop[0])
        self.assertEqual(summary["result"], "STOPPED")
        self.assertTrue(cancelled[0])
        self.assertTrue(self.overlay.close.called)
        self.assertTrue(archive.exists())

    def test_alpha_logs_are_bounded_and_dropped_entries_are_counted(self):
        with patch.object(probe, "ALPHA_EVENT_LOG_LIMIT", 10):
            session, _, summary = self.run_probe(seconds=None, mode="alpha",
                                               should_stop=lambda: self.clock.now >= 1.0)
        self.assertGreater(summary["log_entries_dropped"], 0)
        self.assertFalse((session / "events.jsonl").exists())

    def test_alpha_native_setup_failure_is_an_error_not_normal_stop(self):
        _, archive, summary = self.run_probe(seconds=None, mode="alpha",
                                            overlay_error=OverlayCaptureError("affinity failed"))
        self.assertEqual(summary["result"], "ERROR")
        self.assertEqual(summary["last_error"], "affinity failed")
        self.assertTrue(archive.exists())

    def test_panel_qc_uses_phase4_archive_and_records_build_identity(self):
        session, archive, summary = self.run_probe(mode="qc_alpha")
        self.assertEqual(summary["result"], "TECHNICAL_PASS")
        self.assertTrue(archive.name.startswith("QC_PHASE4_RESULT_"))
        meta = json.loads((session / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["build_id"], summary["build_id"])
        self.assertEqual(len(meta["code_sha256"]), 64)

    def test_stopping_qc_early_does_not_report_pass(self):
        _, archive, summary = self.run_probe(mode="qc_alpha", should_stop=lambda: self.clock.now >= 0.12)
        self.assertEqual(summary["result"], "INTERRUPTED")
        self.assertEqual(summary["stop_reason"], "stopped")
        self.assertTrue(archive.exists())


class ProofCaptureTests(unittest.TestCase):
    def test_alt_tab_during_proof_delay_skips_capture_and_restores_exclusion(self):
        overlay, capture, game = Mock(), Mock(), Mock()
        overlay.set_capture_exclusion.return_value = True
        game.is_game_foreground.side_effect = [True, False]
        with patch.object(probe.asyncio, "sleep", AsyncMock()):
            result = asyncio.run(probe.capture_overlay_proof(overlay, capture, None, Path("unused.png"), game))
        self.assertFalse(result)
        self.assertFalse(capture.grab.called)
        self.assertEqual(overlay.set_capture_exclusion.call_args.args, (True,))

    def test_proof_is_never_started_over_another_foreground_app(self):
        overlay, capture, game = Mock(), Mock(), Mock()
        game.is_game_foreground.return_value = False
        result = asyncio.run(probe.capture_overlay_proof(overlay, capture, None, Path("unused.png"), game))
        self.assertFalse(result)
        self.assertFalse(capture.grab.called)
        self.assertFalse(overlay.set_capture_exclusion.called)
