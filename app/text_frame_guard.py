"""Compare warm dialogue glyphs without reacting to dark animated scenery."""
from __future__ import annotations

from math import ceil, floor
from PIL import Image, ImageChops

from .capture import CapturedFrame
from .models import Rect


def glyph_patch(frame: CapturedFrame, box: Rect) -> Image.Image:
    image = Image.frombytes("RGB", (frame.width, frame.height), frame.bgra, "raw", "BGRX")
    image = image.crop((max(0, floor(box.x) - 6), max(0, floor(box.y) - 4),
                        min(frame.width, ceil(box.right) + 6), min(frame.height, ceil(box.bottom) + 6)))
    red, green, blue = image.split()
    light = ImageChops.darker(red.point(lambda p: 255 if p >= 140 else 0),
                             green.point(lambda p: 255 if p >= 120 else 0))
    # Warm/neutral text; blue effects behind a translucent panel do not count.
    warm = ImageChops.subtract(blue, red).point(lambda p: 255 if p <= 20 else 0)
    return ImageChops.darker(light, warm)


def source_text_changed(before: CapturedFrame, after: CapturedFrame, box: Rect,
                        *, tolerance: float = 0.22) -> bool:
    if (before.width, before.height, before.region) != (after.width, after.height, after.region):
        return True
    old, new = glyph_patch(before, box), glyph_patch(after, box)
    union = ImageChops.lighter(old, new).histogram()[255]
    changed = ImageChops.difference(old, new).histogram()[255]
    return union >= 30 and changed / union > tolerance
