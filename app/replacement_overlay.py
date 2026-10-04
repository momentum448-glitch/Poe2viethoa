from __future__ import annotations

import ctypes
from dataclasses import dataclass
from statistics import median
import sys
from typing import Iterable

from PIL import Image

from .capture import CaptureRegion, CapturedFrame
from .models import Rect


TRANSPARENT_KEY = "#010203"
TEXT_COLOR = "#eee4c9"
WDA_NONE = 0x00000000
WDA_EXCLUDEFROMCAPTURE = 0x00000011

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000


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

    user32 = ctypes.windll.user32
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == -4
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass

    try:
        # PROCESS_PER_MONITOR_DPI_AWARE == 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
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
) -> OverlayRect:
    """Translate OCR-relative dialogue geometry into an absolute screen rectangle.

    Width is allowed to grow slightly for Vietnamese, while height is capped so
    the replacement does not cover the Continue button below the dialogue.
    """

    left = int(round(capture_region.left + dialogue_box.x - horizontal_padding))
    top = int(round(capture_region.top + dialogue_box.y - vertical_padding))

    width = int(round(dialogue_box.w + horizontal_padding * 2))
    width = max(260, min(width, 520))

    # Rendering code can use less than this maximum, but the geometry is
    # intentionally generous enough for one extra wrapped Vietnamese line.
    height = int(round(dialogue_box.h + vertical_padding * 2 + 24))
    height = max(58, min(height, 108))

    roi_left = capture_region.left
    roi_top = capture_region.top
    roi_right = capture_region.left + capture_region.width
    # Leave the lower ~30% of the OCR ROI untouched; that is where Continue and
    # unrelated HUD/chat elements are commonly observed.
    roi_safe_bottom = capture_region.top + int(round(capture_region.height * 0.70))

    left = max(roi_left, min(left, roi_right - width))
    top = max(roi_top, min(top, roi_safe_bottom - height))

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

        enable_per_monitor_dpi_awareness()

        import tkinter as tk
        import tkinter.font as tkfont

        self._tk = tk
        self._tkfont = tkfont
        self.monitor = monitor
        self._user32 = ctypes.windll.user32

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg=TRANSPARENT_KEY)
        self.root.attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", TRANSPARENT_KEY)

        width = int(monitor["width"])
        height = int(monitor["height"])
        left = int(monitor.get("left", 0))
        top = int(monitor.get("top", 0))
        self.root.geometry(f"{width}x{height}+{left}+{top}")

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
        self.hwnd = int(self.root.winfo_id())

        ex_style = int(self._user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE))
        ex_style |= (
            WS_EX_LAYERED
            | WS_EX_TRANSPARENT
            | WS_EX_TOOLWINDOW
            | WS_EX_NOACTIVATE
        )
        self._user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, ex_style)

        self.capture_exclusion_ok = self.set_capture_exclusion(True)
        self._last_render: OverlayRenderInfo | None = None
        self.clear()

    def set_capture_exclusion(self, enabled: bool) -> bool:
        affinity = WDA_EXCLUDEFROMCAPTURE if enabled else WDA_NONE
        ok = bool(self._user32.SetWindowDisplayAffinity(self.hwnd, affinity))
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
        max_text_width = max(80, rect.width - inner_pad_x * 2)
        max_text_height = max(30, rect.height - inner_pad_y * 2)

        font_size, lines, line_height = self._fit_text(
            text,
            max_width=max_text_width,
            max_height=max_text_height,
        )

        needed_height = min(
            rect.height,
            max(
                40,
                line_height * len(lines) + inner_pad_y * 2,
            ),
        )
        draw_rect = OverlayRect(
            left=rect.left,
            top=rect.top,
            width=rect.width,
            height=needed_height,
        )

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
            size=font_size,
            weight="normal",
        )
        self.canvas.create_text(
            local_x + inner_pad_x,
            local_y + inner_pad_y,
            anchor="nw",
            text="\n".join(lines),
            fill=TEXT_COLOR,
            font=font,
            justify="left",
        )

        self.root.lift()
        self.root.attributes("-topmost", True)
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
        for size in range(17, 10, -1):
            font = self._tkfont.Font(family="Segoe UI", size=size)
            lines = self._wrap_pixels(text, font, max_width)
            line_height = int(font.metrics("linespace"))
            if line_height * len(lines) <= max_height:
                return size, lines, line_height

        font = self._tkfont.Font(family="Segoe UI", size=10)
        lines = self._wrap_pixels(text, font, max_width)
        return 10, lines, int(font.metrics("linespace"))

    @staticmethod
    def _wrap_pixels(text: str, font, max_width: int) -> list[str]:
        words = text.split()
        if not words:
            return [""]

        lines: list[str] = []
        current = words[0]

        for word in words[1:]:
            candidate = current + " " + word
            if font.measure(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word

        lines.append(current)
        return lines
