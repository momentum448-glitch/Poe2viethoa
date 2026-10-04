from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import mss


@dataclass(frozen=True)
class CaptureRegion:
    left: int
    top: int
    width: int
    height: int

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


class ScreenCapture:
    """MSS screen capture with resolution-scaled dialogue ROI."""

    def __init__(self) -> None:
        self._sct = mss.mss()

    def close(self) -> None:
        self._sct.close()

    def primary_monitor(self) -> dict[str, Any]:
        return dict(self._sct.monitors[1])

    def default_dialogue_region(self) -> CaptureRegion:
        monitor = self._sct.monitors[1]

        # Wide enough to include both normal and inventory-open dialogue layouts,
        # but excludes most of the minimap and bottom HUD.
        left = monitor["left"] + round(monitor["width"] * 0.12)
        top = monitor["top"] + round(monitor["height"] * 0.39)
        width = round(monitor["width"] * 0.62)
        height = round(monitor["height"] * 0.25)

        return CaptureRegion(left, top, width, height)

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
