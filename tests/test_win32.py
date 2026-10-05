import ctypes
from ctypes import wintypes
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.game_window import ForegroundWindow, GameWindowProbe
from app.capture import CaptureRegion
from app.win32 import configure_user32


class Win32BoundaryTests(unittest.TestCase):
    def test_browser_or_console_with_game_title_is_not_a_game_window(self):
        for cls in ("Chrome_WidgetWin_1", "MozillaWindowClass", "ConsoleWindowClass", "", "poe-tool"):
            self.assertFalse(ForegroundWindow(1, "Path of Exile 2", cls).is_poe2)

    def test_native_game_class_is_recognized_without_relying_on_title(self):
        self.assertTrue(ForegroundWindow(1, "", "POEWindowClass").is_poe2)
        self.assertTrue(ForegroundWindow(1, "Path of Exile 2", "POE2WindowClass").is_poe2)

    def test_native_handles_are_pointer_sized_for_returns_and_arguments(self):
        user32 = configure_user32(Mock())
        for name in ("GetForegroundWindow", "GetAncestor"):
            self.assertEqual(ctypes.sizeof(getattr(user32, name).restype), ctypes.sizeof(ctypes.c_void_p))
        self.assertEqual(user32.SetWindowDisplayAffinity.argtypes[0], wintypes.HWND)
        self.assertEqual(user32.GetWindowTextW.argtypes[0], wintypes.HWND)
        self.assertEqual(user32.GetClientRect.argtypes, [wintypes.HWND, ctypes.POINTER(wintypes.RECT)])
        self.assertEqual(user32.ClientToScreen.argtypes, [wintypes.HWND, ctypes.POINTER(wintypes.POINT)])

    def test_client_bounds_are_mapped_to_physical_desktop_coordinates(self):
        user32 = Mock()
        handle = 0x123456789
        user32.GetForegroundWindow.return_value = handle
        user32.GetWindowTextLengthW.return_value = 0
        user32.GetClassNameW.side_effect = lambda hwnd, buf, count: setattr(buf, "value", "POEWindowClass")

        def rect(hwnd, pointer):
            self.assertEqual(hwnd, handle)
            pointer._obj.right, pointer._obj.bottom = 1280, 720
            return True

        def origin(hwnd, pointer):
            self.assertEqual(hwnd, handle)
            pointer._obj.x, pointer._obj.y = -1700, 100
            return True

        user32.GetClientRect.side_effect = rect
        user32.ClientToScreen.side_effect = origin
        with patch("app.game_window.sys.platform", "win32"), \
             patch("app.game_window.get_user32", return_value=user32):
            probe = GameWindowProbe()
            window = probe.foreground()
            self.assertEqual(window.client_region, CaptureRegion(-1700, 100, 1280, 720))
            self.assertTrue(probe.is_current(window))
            user32.GetClientRect.return_value = False
            user32.GetClientRect.side_effect = None
            self.assertIsNone(probe.foreground().client_region)
            self.assertFalse(probe.is_current(window))

    def test_inflight_work_is_invalidated_when_same_game_window_moves_or_resizes(self):
        initial = ForegroundWindow(1, "", "POEWindowClass", CaptureRegion(0, 0, 1920, 1080))
        probe = GameWindowProbe.__new__(GameWindowProbe)
        for region in (CaptureRegion(10, 0, 1920, 1080), CaptureRegion(0, 0, 1280, 720)):
            with patch.object(probe, "foreground", return_value=ForegroundWindow(1, "", "POEWindowClass", region)):
                self.assertFalse(probe.is_current(initial))

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
