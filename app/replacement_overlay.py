from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from math import ceil, floor
from statistics import median
import sys

from PIL import Image

from .capture import CaptureRegion, CapturedFrame
from .models import Rect
from .win32 import (
    GA_ROOT, HWND_TOPMOST, SWP_FRAMECHANGED, SWP_NOACTIVATE,
    SWP_NOMOVE, SWP_NOSIZE, get_user32,
)


TRANSPARENT_KEY = "#010203"
TEXT_COLOR = "#eee4c9"
WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000


class OverlayCaptureError(RuntimeError):
    """Capture exclusion failed; runtime capture must stop immediately."""


class OverlayLayoutError(RuntimeError):
    """The complete translation cannot fit without covering other controls."""


@dataclass(frozen=True)
class OverlayRect:
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

    def to_dict(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class OverlayRenderInfo:
    rect: OverlayRect
    font_size: int
    lines: tuple[str, ...]
    cover_color: str

    def to_dict(self) -> dict[str, object]:
        return {
            "rect": self.rect.to_dict(),
            "font_size": self.font_size,
            "lines": list(self.lines),
            "cover_color": self.cover_color,
        }


def enable_per_monitor_dpi_awareness() -> None:
    """Best-effort physical-pixel coordinates for MSS/Tk alignment on Windows."""
    if sys.platform != "win32":
        return

    user32 = get_user32()
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass

    try:
        # PROCESS_PER_MONITOR_DPI_AWARE == 2
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
        shcore.SetProcessDpiAwareness.restype = ctypes.c_long
        shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def build_overlay_rect(
    dialogue_box: Rect,
    capture_region: CaptureRegion,
    *,
    horizontal_padding: int = 10,
    vertical_padding: int = 6,
    continue_box: Rect | None = None,
) -> OverlayRect:
    """Cover every source pixel, bounded by the actual Continue button if found."""
    roi_left = capture_region.left
    roi_top = capture_region.top
    roi_right = capture_region.left + capture_region.width
    roi_bottom = capture_region.top + capture_region.height
    source_left = roi_left + floor(dialogue_box.x)
    source_top = roi_top + floor(dialogue_box.y)
    source_right = roi_left + ceil(dialogue_box.right)
    source_bottom = roi_top + ceil(dialogue_box.bottom)

    safe_bottom = roi_bottom
    if continue_box is not None:
        safe_bottom = min(safe_bottom, roi_top + floor(continue_box.y) - 3)
    if (dialogue_box.w <= 0 or dialogue_box.h <= 0
            or source_left < roi_left or source_top < roi_top
            or source_right > roi_right or source_bottom > safe_bottom):
        raise OverlayLayoutError("Dialogue mask would clip source text or cover Continue.")

    width = min(capture_region.width, max(260, source_right - source_left + 2 * horizontal_padding))
    left = max(roi_left, min(source_left - horizontal_padding, roi_right - width))
    top = max(roi_top, source_top - vertical_padding)
    minimum_height = source_bottom - top
    desired_height = max(58, minimum_height + vertical_padding + 24)
    height = min(max(minimum_height, min(108, desired_height)), safe_bottom - top)

    return OverlayRect(left=left, top=top, width=width, height=height)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def estimate_cover_color(frame: CapturedFrame, dialogue_box: Rect) -> str:
    """Estimate the dark dialogue-panel color under the English text.

    The PoE2 panel is textured, so a perfect clone is impossible with a solid
    fill. Using the median of dark pixels inside/around the text box produces a
    visually quiet mask and is much closer than a fixed black rectangle.
    """

    image = Image.frombytes(
        "RGB",
        (frame.width, frame.height),
        frame.bgra,
        "raw",
        "BGRX",
    )

    pad = 8
    x0 = max(0, int(dialogue_box.x) - pad)
    y0 = max(0, int(dialogue_box.y) - pad)
    x1 = min(frame.width, int(dialogue_box.right) + pad)
    y1 = min(frame.height, int(dialogue_box.bottom) + pad)

    crop = image.crop((x0, y0, x1, y1))
    dark: list[tuple[int, int, int]] = []

    for r, g, b in crop.getdata():
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        if luminance <= 95:
            dark.append((r, g, b))

    if not dark:
        return "#17130f"

    rs = sorted(p[0] for p in dark)
    gs = sorted(p[1] for p in dark)
    bs = sorted(p[2] for p in dark)
    color = (int(median(rs)), int(median(gs)), int(median(bs)))

    # Keep the cover dark enough that the light Vietnamese text remains legible.
    color = tuple(min(58, max(8, c)) for c in color)
    return rgb_to_hex(color)


class ReplacementOverlay:
    """Topmost click-through Windows overlay for Vietnamese dialogue."""

    def __init__(self, monitor: dict[str, int]) -> None:
        if sys.platform != "win32":
            raise RuntimeError("ReplacementOverlay is Windows-only.")
        if sys.getwindowsversion().build < 19041:
            raise OverlayCaptureError("Phase 3 needs Windows 10 build 19041 or newer for capture exclusion.")

        enable_per_monitor_dpi_awareness()

        import tkinter as tk
        import tkinter.font as tkfont

        self._tk = tk
        self._tkfont = tkfont
        self.monitor = monitor
        self._user32 = get_user32()

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.configure(bg=TRANSPARENT_KEY)
        self.root.attributes("-topmost", True)
        self.root.wm_attributes("-toolwindow", True)
        self.root.wm_attributes("-transparentcolor", TRANSPARENT_KEY)

        width = int(monitor["width"])
        height = int(monitor["height"])
        left = int(monitor.get("left", 0))
        top = int(monitor.get("top", 0))
        self.root.geometry(f"{width}x{height}+0+0")

        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Materialize the native HWND before applying extended window styles.
        self.root.update_idletasks()
        self.root.update()
        # winfo_id is Tk's child HWND. Styles and affinity belong to its wrapper.
        self.hwnd = int(self._user32.GetAncestor(int(self.root.wm_frame(), 0), GA_ROOT) or 0)
        if not self.hwnd:
            self.root.destroy()
            raise OverlayCaptureError("Could not resolve the overlay's top-level HWND.")

        ex_style = int(self._user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE))
        ex_style |= (
            WS_EX_LAYERED
            | WS_EX_TRANSPARENT
            | WS_EX_TOOLWINDOW
            | WS_EX_NOACTIVATE
        )
        self._user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, ex_style)

        applied_style = int(self._user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE))
        if applied_style & ex_style != ex_style:
            self.root.destroy()
            raise OverlayCaptureError("Windows could not apply click-through/no-activation styles.")

        self.capture_exclusion_ok = self.set_capture_exclusion(True)
        self._last_render: OverlayRenderInfo | None = None
        self._render_font = None
        self.clear()
        self.root.deiconify()
        self.pump()
        if not self._user32.SetWindowPos(
            self.hwnd, HWND_TOPMOST, left, top, width, height,
            SWP_NOACTIVATE | SWP_FRAMECHANGED,
        ):
            self.root.destroy()
            raise OverlayCaptureError("Windows could not position the overlay.")

    def set_capture_exclusion(self, enabled: bool) -> bool:
        affinity = WDA_EXCLUDEFROMCAPTURE if enabled else WDA_NONE
        ok = bool(self._user32.SetWindowDisplayAffinity(self.hwnd, affinity))
        if ok:
            actual = wintypes.DWORD()
            ok = bool(self._user32.GetWindowDisplayAffinity(self.hwnd, ctypes.byref(actual)))
            ok = ok and actual.value == affinity
        self.root.update_idletasks()
        self.root.update()
        return ok

    def clear(self) -> None:
        self.canvas.delete("all")
        self._last_render = None
        self.root.update_idletasks()
        self.root.update()

    def close(self) -> None:
        try:
            self.set_capture_exclusion(False)
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def pump(self) -> None:
        self.root.update_idletasks()
        self.root.update()

    def show_translation(
        self,
        rect: OverlayRect,
        text: str,
        *,
        cover_color: str,
    ) -> OverlayRenderInfo:
        self.canvas.delete("all")

        local_x = rect.left - int(self.monitor.get("left", 0))
        local_y = rect.top - int(self.monitor.get("top", 0))

        inner_pad_x = 8
        inner_pad_y = 5
        max_text_width = max(1, rect.width - inner_pad_x * 2)
        max_text_height = max(1, rect.height - inner_pad_y * 2)

        font_size, lines, line_height = self._fit_text(
            text,
            max_width=max_text_width,
            max_height=max_text_height,
        )

        # A shorter Vietnamese translation must still mask ALL English lines.
        draw_rect = rect

        self.canvas.create_rectangle(
            local_x,
            local_y,
            local_x + draw_rect.width,
            local_y + draw_rect.height,
            fill=cover_color,
            outline=cover_color,
            width=0,
        )

        font = self._tkfont.Font(
            family="Segoe UI",
            size=-font_size,
            weight="normal",
        )
        self._render_font = font
        self.canvas.create_text(
            local_x + inner_pad_x,
            local_y + inner_pad_y,
            anchor="nw",
            text="\n".join(lines),
            fill=TEXT_COLOR,
            font=font,
            justify="left",
        )

        if not self._user32.SetWindowPos(
            self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
        ):
            raise OverlayCaptureError("Windows could not keep the overlay topmost.")
        self.root.update_idletasks()
        self.root.update()

        info = OverlayRenderInfo(
            rect=draw_rect,
            font_size=font_size,
            lines=tuple(lines),
            cover_color=cover_color,
        )
        self._last_render = info
        return info

    def _fit_text(
        self,
        text: str,
        *,
        max_width: int,
        max_height: int,
    ) -> tuple[int, list[str], int]:
        for size in range(23, 11, -1):
            # Negative Tk font sizes are physical pixels, independent of DPI.
            font = self._tkfont.Font(family="Segoe UI", size=-size)
            lines = self._wrap_pixels(text, font, max_width)
            line_height = int(font.metrics("linespace"))
            if (line_height * len(lines) <= max_height
                    and all(font.measure(line) <= max_width for line in lines)):
                return size, lines, line_height
        raise OverlayLayoutError("Vietnamese text does not fit inside the dialogue mask.")

    @staticmethod
    def _wrap_pixels(text: str, font, max_width: int) -> list[str]:
        words = text.split()
        if not words:
            return [""]

        lines: list[str] = []
        current = ""

        for word in words:
            if font.measure(word) > max_width:
                if current:
                    lines.append(current)
                    current = ""
                for char in word:
                    if current and font.measure(current + char) > max_width:
                        lines.append(current)
                        current = ""
                    current += char
                continue
            candidate = (current + " " + word).strip()
            if font.measure(candidate) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)
        return lines
