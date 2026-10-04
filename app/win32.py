from __future__ import annotations

import ctypes
from ctypes import wintypes
from functools import lru_cache


GA_ROOT = 2
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020


def configure_user32(user32):
    """Use pointer-sized HWNDs; ctypes otherwise defaults to 32-bit integers."""
    signatures = {
        "GetForegroundWindow": ([], wintypes.HWND),
        "GetAncestor": ([wintypes.HWND, wintypes.UINT], wintypes.HWND),
        "GetWindowTextLengthW": ([wintypes.HWND], ctypes.c_int),
        "GetWindowTextW": (
            [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int,
        ),
        "GetClassNameW": (
            [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int,
        ),
        "GetWindowLongW": ([wintypes.HWND, ctypes.c_int], wintypes.LONG),
        "SetWindowLongW": (
            [wintypes.HWND, ctypes.c_int, wintypes.LONG], wintypes.LONG,
        ),
        "SetWindowPos": (
            [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
             ctypes.c_int, ctypes.c_int, wintypes.UINT], wintypes.BOOL,
        ),
        "SetWindowDisplayAffinity": (
            [wintypes.HWND, wintypes.DWORD], wintypes.BOOL,
        ),
        "GetWindowDisplayAffinity": (
            [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL,
        ),
        "SetProcessDpiAwarenessContext": ([ctypes.c_void_p], wintypes.BOOL),
        "SetProcessDPIAware": ([], wintypes.BOOL),
    }
    for name, (argtypes, restype) in signatures.items():
        function = getattr(user32, name, None)
        if function is not None:
            function.argtypes = argtypes
            function.restype = restype
    return user32


@lru_cache(maxsize=1)
def get_user32():
    return configure_user32(ctypes.WinDLL("user32", use_last_error=True))
