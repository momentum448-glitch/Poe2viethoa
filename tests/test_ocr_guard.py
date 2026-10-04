import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app import session_runtime as runtime


class OcrGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_foreground_loss_is_not_forgotten_if_game_returns_before_ocr_finishes(self):
        foreground = [True]
        hidden = Mock()

        async def recognize(*args):
            foreground[0] = False
            await asyncio.sleep(0.13)
            foreground[0] = True
            return "recognized"

        ocr = SimpleNamespace(recognize_bgra=recognize)
        frame = SimpleNamespace(bgra=b"", width=1, height=1)
        result, lost = await runtime.recognize_guarded(
            ocr, frame, is_foreground=lambda: foreground[0], should_stop=lambda: False,
            on_foreground_loss=hidden,
        )
        self.assertEqual(result, "recognized")
        self.assertTrue(lost)
        hidden.assert_called()

    async def test_timeout_cancels_pending_ocr_and_releases_its_resources(self):
        closed = [False]

        async def recognize(*args):
            try:
                await asyncio.Future()
            finally:
                closed[0] = True

        frame = SimpleNamespace(bgra=b"", width=1, height=1)
        with patch.object(runtime, "OCR_TIMEOUT_SECONDS", 0.01), self.assertRaises(TimeoutError):
            await runtime.recognize_guarded(
                SimpleNamespace(recognize_bgra=recognize), frame, is_foreground=lambda: True,
                should_stop=lambda: False, on_foreground_loss=Mock(),
            )
        self.assertTrue(closed[0])
