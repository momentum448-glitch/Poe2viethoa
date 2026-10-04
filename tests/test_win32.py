import ctypes
from ctypes import wintypes
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.game_window import GameWindowProbe
from app.win32 import configure_user32


class Win32BoundaryTests(unittest.TestCase):
    def test_native_handles_are_pointer_sized_for_returns_and_arguments(self):
        user32 = configure_user32(Mock())
        for name in ("GetForegroundWindow", "GetAncestor"):
            self.assertEqual(ctypes.sizeof(getattr(user32, name).restype), ctypes.sizeof(ctypes.c_void_p))
        self.assertEqual(user32.SetWindowDisplayAffinity.argtypes[0], wintypes.HWND)
        self.assertEqual(user32.GetWindowTextW.argtypes[0], wintypes.HWND)

    def test_null_foreground_handle_is_a_valid_background_state(self):
        probe = GameWindowProbe.__new__(GameWindowProbe)
        probe._user32 = SimpleNamespace(GetForegroundWindow=lambda: None)
        self.assertFalse(probe.foreground().is_poe2)

    def test_foreground_probe_preserves_a_64_bit_handle(self):
        user32 = Mock()
        handle = 0x123456789
        user32.GetForegroundWindow.return_value = handle
        user32.GetWindowTextLengthW.return_value = 15

        def text(hwnd, buffer, count):
            self.assertEqual(hwnd, handle)
            buffer.value = "Path of Exile 2"
            return 15

        def class_name(hwnd, buffer, count):
            buffer.value = "POEWindowClass"
            return 14

        user32.GetWindowTextW.side_effect = text
        user32.GetClassNameW.side_effect = class_name
        with patch("app.game_window.sys.platform", "win32"), \
             patch("app.game_window.get_user32", return_value=user32):
            foreground = GameWindowProbe().foreground()
        self.assertEqual(foreground.hwnd, handle)
        self.assertTrue(foreground.is_poe2)
