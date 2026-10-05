from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import sys

from .win32 import get_user32
from .capture import CaptureRegion


@dataclass(frozen=True)
class ForegroundWindow:
    hwnd: int
    title: str
    class_name: str
    client_region: CaptureRegion | None = None

    @property
    def is_poe2(self) -> bool:
        cls = self.class_name.casefold().strip()
        # A browser/document can have exactly the game's title. Only the native
        # game window classes qualify for capture; a title alone never does.
        return cls in {"poewindowclass", "poe2windowclass"}


class GameWindowProbe:
    """Small Win32 foreground-window adapter with no external dependency."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("GameWindowProbe is Windows-only.")
        self._user32 = get_user32()

    def foreground(self) -> ForegroundWindow:
        hwnd = int(self._user32.GetForegroundWindow() or 0)
        if not hwnd:
            return ForegroundWindow(0, "", "")

        title_len = self._user32.GetWindowTextLengthW(hwnd)
        title_buf = ctypes.create_unicode_buffer(max(1, title_len + 1))
        self._user32.GetWindowTextW(hwnd, title_buf, len(title_buf))

        class_buf = ctypes.create_unicode_buffer(256)
        self._user32.GetClassNameW(hwnd, class_buf, len(class_buf))

        window = ForegroundWindow(
            hwnd=hwnd,
            title=title_buf.value,
            class_name=class_buf.value,
        )
        if not window.is_poe2:
            return window
        rect, origin = wintypes.RECT(), wintypes.POINT()
        if (self._user32.GetClientRect(hwnd, ctypes.byref(rect))
                and self._user32.ClientToScreen(hwnd, ctypes.byref(origin))
                and rect.right > rect.left and rect.bottom > rect.top):
            return ForegroundWindow(hwnd, window.title, window.class_name,
                                    CaptureRegion(origin.x, origin.y,
                                                  rect.right - rect.left, rect.bottom - rect.top))
        return window

    def is_game_foreground(self) -> bool:
        return self.foreground().is_poe2

    def is_current(self, window: ForegroundWindow) -> bool:
        """Also invalidate an in-flight capture when the game moves/resizes."""
        current = self.foreground()
        return (current.is_poe2 and current.hwnd == window.hwnd
                and current.client_region == window.client_region)
