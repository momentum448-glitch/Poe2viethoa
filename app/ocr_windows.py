from __future__ import annotations

import time
from PIL import Image

from .models import OcrLine, OcrResult, OcrWord, Rect


class WindowsOcr:
    """Windows Media OCR adapter.

    The runtime keeps this behind a small adapter so another OCR backend can be
    tested later without changing capture/context/matching code.
    """

    def __init__(self) -> None:
        from winrt.windows.media.ocr import OcrEngine

        self._engine = OcrEngine.try_create_from_user_profile_languages()
        self._max_dimension = int(OcrEngine.max_image_dimension)
        if self._max_dimension <= 0:
            raise RuntimeError("Windows OCR returned an invalid image dimension limit.")
        if self._engine is None:
            raise RuntimeError(
                "Windows OCR is unavailable. Install the English OCR language capability."
            )

    async def recognize_bgra(self, bgra: bytes, width: int, height: int) -> OcrResult:
        from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
        from winrt.windows.storage.streams import DataWriter

        started = time.perf_counter()
        original_width, original_height = width, height
        if max(width, height) > self._max_dimension:
            # Whole-client discovery may exceed the engine limit on 4K displays.
            # Restore all word coordinates to the captured physical-pixel frame.
            scale = self._max_dimension / max(width, height)
            resized = Image.frombytes("RGBA", (width, height), bgra, "raw", "BGRA").resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )
            width, height = resized.size
            bgra = resized.tobytes("raw", "BGRA")
        scale_x, scale_y = original_width / width, original_height / height
        writer = DataWriter()
        bitmap = None
        try:
            try:
                writer.write_bytes(bgra)
            except TypeError:
                writer.write_bytes(list(bgra))

            bitmap = SoftwareBitmap(BitmapPixelFormat.BGRA8, width, height)
            bitmap.copy_from_buffer(writer.detach_buffer())
            raw = await self._engine.recognize_async(bitmap)
        finally:
            try:
                writer.close()
            except Exception:
                pass
            if bitmap is not None:
                try:
                    bitmap.close()
                except Exception:
                    pass

        lines: list[OcrLine] = []
        for raw_line in raw.lines:
            words: list[OcrWord] = []
            xs: list[float] = []
            ys: list[float] = []
            rights: list[float] = []
            bottoms: list[float] = []

            for raw_word in raw_line.words:
                rect = raw_word.bounding_rect
                box = Rect(
                    float(rect.x) * scale_x,
                    float(rect.y) * scale_y,
                    float(rect.width) * scale_x,
                    float(rect.height) * scale_y,
                )
                words.append(OcrWord(raw_word.text, box))
                xs.append(box.x)
                ys.append(box.y)
                rights.append(box.right)
                bottoms.append(box.bottom)

            line_box = None
            if words:
                x = min(xs)
                y = min(ys)
                line_box = Rect(x, y, max(rights) - x, max(bottoms) - y)

            lines.append(OcrLine(raw_line.text, line_box, words))

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return OcrResult(raw.text, lines, elapsed_ms)
