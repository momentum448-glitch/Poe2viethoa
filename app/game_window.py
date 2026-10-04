from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import sys


@dataclass(frozen=True)
class ForegroundWindow:
    hwnd: int
    title: str
    class_name: str

    @property
    def is_poe2(self) -> bool:
        title = self.title.casefold()
        cls = self.class_name.casefold()
        return (
            cls == "poewindowclass"
            or "path of exile 2" in title
            or title == "path of exile"
        )


class GameWindowProbe:
    """Small Win32 foreground-window adapter with no external dependency."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("GameWindowProbe is Windows-only.")
        self._user32 = ctypes.windll.user32

    def foreground(self) -> ForegroundWindow:
        hwnd = int(self._user32.GetForegroundWindow())
        if not hwnd:
            return ForegroundWindow(0, "", "")

        title_len = self._user32.GetWindowTextLengthW(hwnd)
        title_buf = ctypes.create_unicode_buffer(max(1, title_len + 1))
        self._user32.GetWindowTextW(hwnd, title_buf, len(title_buf))

        class_buf = ctypes.create_unicode_buffer(256)
        self._user32.GetClassNameW(hwnd, class_buf, len(class_buf))

        return ForegroundWindow(hwnd, title_buf.value, class_buf.value)

    def is_game_foreground(self) -> bool:
        return self.foreground().is_poe2
