"""Coordinate handling for discovery of, and subsequent tracking of, an NPC panel."""
from __future__ import annotations

from math import ceil, floor

from .capture import CaptureRegion
from .models import DialogueContext, Rect


def absolute_box(box: Rect, region: CaptureRegion) -> Rect:
    return box.translated(region.left, region.top)


def tracking_region(context: DialogueContext, captured: CaptureRegion,
                    viewport: CaptureRegion) -> CaptureRegion:
    """Keep the paragraph and anchors, padded for neighboring page lengths.

    Only shrink inside the frame already captured: the glyph reference can be
    cropped to exactly the same coordinates, with no accidental stale reset.
    """
    box = context.dialogue_box
    if not context.detected or box is None:
        return viewport
    box = absolute_box(box, captured)
    header = absolute_box(context.speaker_box, captured) if context.speaker_box else None
    footer = absolute_box(context.continue_box, captured) if context.continue_box else None
    # Font size from local anchors, bounded when the body spans many lines.
    font_height = max(12, header.h if header else footer.h if footer else min(28, box.h))
    right = max(box.right, box.x + font_height * 28)
    if footer:
        right = max(right, 2 * footer.cx - box.x)
    left = max(viewport.left, captured.left, floor(box.x - font_height * 3))
    top = max(viewport.top, captured.top,
              floor(min(box.y, header.y if header else box.y - font_height * 3) - font_height * 2))
    right = min(viewport.right, captured.right, ceil(right + font_height * 3))
    bottom = min(viewport.bottom, captured.bottom,
                 ceil(max(box.bottom + font_height * 5, box.y + font_height * 12,
                          footer.bottom + font_height * 4 if footer else box.bottom)))
    return CaptureRegion(left, top, right - left, bottom - top)


def proof_key(source_id: str, box: Rect, region: CaptureRegion) -> tuple[str, int, int]:
    absolute = absolute_box(box, region)
    return source_id, round(absolute.x), round(absolute.y)


def position_was_proofed(key: tuple[str, int, int],
                        positions: set[tuple[str, int, int]]) -> bool:
    # A distance check tolerates OCR jitter even at a grid-cell boundary.
    return any(old[0] == key[0] and max(abs(old[1] - key[1]), abs(old[2] - key[2])) < 24
               for old in positions)
