import asyncio
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.ocr_windows import WindowsOcr


class OcrResourceTests(unittest.TestCase):
    def test_oversized_discovery_is_resized_and_word_boxes_return_to_screen_pixels(self):
        writer, bitmap = Mock(), Mock()
        imaging = ModuleType("winrt.windows.graphics.imaging")
        imaging.BitmapPixelFormat = SimpleNamespace(BGRA8=1)
        imaging.SoftwareBitmap = Mock(return_value=bitmap)
        streams = ModuleType("winrt.windows.storage.streams")
        streams.DataWriter = Mock(return_value=writer)
        raw_word = SimpleNamespace(text="Renly", bounding_rect=SimpleNamespace(x=50, y=5, width=20, height=6))
        raw = SimpleNamespace(text="Renly", lines=[SimpleNamespace(text="Renly", words=[raw_word])])
        ocr = WindowsOcr.__new__(WindowsOcr)
        ocr._max_dimension = 1000
        ocr._engine = SimpleNamespace(recognize_async=AsyncMock(return_value=raw))
        with patch.dict(sys.modules, {imaging.__name__: imaging, streams.__name__: streams}):
            result = asyncio.run(ocr.recognize_bgra(b"\x00\x00\x00\xff" * 400000, 4000, 100))
        imaging.SoftwareBitmap.assert_called_once_with(1, 1000, 25)
        self.assertEqual(len(writer.write_bytes.call_args.args[0]), 100000)
        box = result.lines[0].words[0].box
        self.assertEqual((box.x, box.y, box.w, box.h), (200, 20, 80, 24))
        self.assertEqual(result.lines[0].box, box)
        bitmap.close.assert_called_once()
        writer.close.assert_called_once()

    def run_ocr(self, outcome):
        writer, bitmap = Mock(), Mock()
        imaging = ModuleType("winrt.windows.graphics.imaging")
        imaging.BitmapPixelFormat = SimpleNamespace(BGRA8=1)
        imaging.SoftwareBitmap = Mock(return_value=bitmap)
        streams = ModuleType("winrt.windows.storage.streams")
        streams.DataWriter = Mock(return_value=writer)
        ocr = WindowsOcr.__new__(WindowsOcr)
        ocr._max_dimension = 2600
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
