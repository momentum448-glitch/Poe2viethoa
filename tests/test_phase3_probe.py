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

from app import phase3_probe as probe
from app.capture import CaptureRegion, CapturedFrame
from app.frame_stabilizer import StabilizerDecision
from app.game_window import ForegroundWindow
from app.models import DialogueContext, OcrResult, Rect
from app.replacement_overlay import OverlayCaptureError, OverlayRenderInfo
from app.translation_models import TranslationRecord
from app.translation_store import build_sqlite


TEXT = "The old bridge has fallen."
CONTEXT = DialogueContext(True, "normal_right", 0.99, "Keeper", TEXT, Rect(10, 4, 35, 8))
NO_DIALOGUE = DialogueContext(False, "unknown", 0.0, None, "", None)


class ProbeLifecycleTests(unittest.TestCase):
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
        self.capture.primary_monitor.return_value = {"left": 0, "top": 0, "width": 64, "height": 32}
        self.capture.default_dialogue_region.return_value = self.region
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
            1, "Path of Exile 2" if self.is_game() else "Other app", "",
        )

    def grab(self, region):
        self.assertTrue(self.is_game(), "Capture must never run over another foreground app")
        return self.frame

    async def sleep(self, seconds):
        self.clock.now += max(0.001, seconds)

    def run_probe(self, *, seconds=0.35, db=None, overlay_error=None):
        replacements = {
            "__file__": str(self.root / "app" / "phase3_probe.py"),
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
            session, archive = asyncio.run(probe.run(seconds, 0.12, db or self.db))
        summary = json.loads((session / "summary.json").read_text(encoding="utf-8"))
        return session, archive, summary

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
        self.assertEqual(self.capture.grab.call_count, 2)  # raw game + QC-only proof
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
