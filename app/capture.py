from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import mss
from PIL import Image


@dataclass(frozen=True)
class CaptureRegion:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def as_mss(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class CapturedFrame:
    bgra: bytes
    width: int
    height: int
    region: CaptureRegion


def crop_frame(frame: CapturedFrame, region: CaptureRegion) -> CapturedFrame:
    """Rebase a captured reference without taking another screen shot."""
    if not (region.width > 0 and region.height > 0
            and frame.region.left <= region.left < region.right <= frame.region.right
            and frame.region.top <= region.top < region.bottom <= frame.region.bottom):
        raise ValueError("The tracking crop must be inside its captured frame.")
    if region == frame.region:
        return frame
    image = Image.frombytes("RGBA", (frame.width, frame.height), frame.bgra, "raw", "BGRA")
    x, y = region.left - frame.region.left, region.top - frame.region.top
    cropped = image.crop((x, y, x + region.width, y + region.height))
    return CapturedFrame(cropped.tobytes("raw", "BGRA"), region.width, region.height, region)


class ScreenCapture:
    """Capture the visible game client; popup tracking uses a measured crop."""

    def __init__(self) -> None:
        self._sct = mss.mss()

    def close(self) -> None:
        self._sct.close()

    def primary_monitor(self) -> dict[str, Any]:
        return dict(self._sct.monitors[1])

    def desktop_monitor(self) -> dict[str, Any]:
        # MSS index 0 is the virtual desktop, including negative monitor origins.
        # The transparent overlay must also cover a game on a secondary monitor.
        return dict(self._sct.monitors[0])

    def game_region(self, client: CaptureRegion | None) -> CaptureRegion | None:
        if client is None or client.width <= 0 or client.height <= 0:
            return None
        desktop = CaptureRegion(**{k: self._sct.monitors[0][k]
                                   for k in ("left", "top", "width", "height")})
        left, top = max(client.left, desktop.left), max(client.top, desktop.top)
        right, bottom = min(client.right, desktop.right), min(client.bottom, desktop.bottom)
        if right <= left or bottom <= top:
            return None
        return CaptureRegion(left, top, right - left, bottom - top)

    def grab(self, region: CaptureRegion) -> CapturedFrame:
        shot = self._sct.grab(region.as_mss())
        return CapturedFrame(
            bgra=bytes(shot.bgra),
            width=shot.width,
            height=shot.height,
            region=region,
        )

    def __enter__(self) -> "ScreenCapture":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
