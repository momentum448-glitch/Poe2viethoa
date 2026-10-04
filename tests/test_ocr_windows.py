import asyncio
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.ocr_windows import WindowsOcr


class OcrResourceTests(unittest.TestCase):
    def run_ocr(self, outcome):
        writer, bitmap = Mock(), Mock()
        imaging = ModuleType("winrt.windows.graphics.imaging")
        imaging.BitmapPixelFormat = SimpleNamespace(BGRA8=1)
        imaging.SoftwareBitmap = Mock(return_value=bitmap)
        streams = ModuleType("winrt.windows.storage.streams")
        streams.DataWriter = Mock(return_value=writer)
        ocr = WindowsOcr.__new__(WindowsOcr)
        ocr._engine = SimpleNamespace(recognize_async=AsyncMock(side_effect=outcome))
        with patch.dict(sys.modules, {imaging.__name__: imaging, streams.__name__: streams}):
            try:
                asyncio.run(ocr.recognize_bgra(b"\0\0\0\0", 1, 1))
            except RuntimeError:
                pass
        return writer, bitmap

    def test_bitmap_and_writer_are_closed_after_success(self):
        writer, bitmap = self.run_ocr([SimpleNamespace(text="", lines=[])])
        writer.close.assert_called_once()
        bitmap.close.assert_called_once()

    def test_bitmap_and_writer_are_closed_after_ocr_failure(self):
        writer, bitmap = self.run_ocr(RuntimeError("OCR failed"))
        writer.close.assert_called_once()
        bitmap.close.assert_called_once()
