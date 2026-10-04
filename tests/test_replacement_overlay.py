import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import tkinter
import tkinter.font

from app.capture import CaptureRegion
from app.models import Rect
from app.replacement_overlay import (
    OverlayLayoutError, ReplacementOverlay, build_overlay_rect, rgb_to_hex,
    WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE,
)
from app.win32 import SWP_NOACTIVATE


class OverlayGeometryTests(unittest.TestCase):
    def test_normal_dialogue_box_translates_to_absolute_screen_pixels(self):
        region = CaptureRegion(left=230, top=421, width=1190, height=270)
        box = Rect(x=449, y=75, w=471, h=60)

        rect = build_overlay_rect(box, region)

        self.assertEqual(rect.left, 661)
        self.assertEqual(rect.top, 490)
        self.assertGreaterEqual(rect.width, 471)
        self.assertLessEqual(rect.height, 108)

    def test_overlay_covers_source_and_stays_above_actual_continue(self):
        region = CaptureRegion(left=230, top=421, width=1190, height=270)
        box = Rect(x=115, y=75, w=470, h=100)
        button = Rect(x=240, y=184, w=75, h=15)

        rect = build_overlay_rect(box, region, continue_box=button)

        self.assertGreaterEqual(rect.bottom, region.top + box.bottom)
        self.assertLess(rect.bottom, region.top + button.y)

    def test_large_source_at_high_resolution_is_not_clipped_to_520_pixels(self):
        region = CaptureRegion(left=460, top=842, width=2380, height=540)
        box = Rect(x=898, y=150, w=942, h=172)
        rect = build_overlay_rect(box, region)
        self.assertLessEqual(rect.left, region.left + box.x)
        self.assertLessEqual(rect.top, region.top + box.y)
        self.assertGreaterEqual(rect.right, region.left + box.right)
        self.assertGreaterEqual(rect.bottom, region.top + box.bottom)

    def test_mask_does_not_move_up_and_leave_the_last_source_line_exposed(self):
        region = CaptureRegion(left=230, top=421, width=1190, height=270)
        box = Rect(x=115, y=155, w=470, h=100)
        rect = build_overlay_rect(box, region)
        self.assertGreaterEqual(rect.bottom, region.top + box.bottom)

    def test_overlapping_control_is_rejected_instead_of_covering_continue(self):
        region = CaptureRegion(0, 0, 1190, 270)
        with self.assertRaises(OverlayLayoutError):
            build_overlay_rect(Rect(115, 75, 470, 100), region,
                               continue_box=Rect(240, 170, 75, 15))

    def test_measured_continue_space_is_available_for_long_translation(self):
        region = CaptureRegion(230, 421, 1190, 486)
        source = Rect(115, 75, 470, 80)
        button = Rect(290, 245, 75, 15)
        limited = build_overlay_rect(source, region)
        expanded = build_overlay_rect(source, region, continue_box=button)
        self.assertGreater(expanded.height, limited.height)
        self.assertLess(expanded.bottom, region.top + button.y)

    def test_rgb_to_hex(self):
        self.assertEqual(rgb_to_hex((23, 19, 15)), "#17130f")


class PixelFont:
    def __init__(self, *, size=-12, **kwargs):
        self.size = abs(size)

    def measure(self, text):
        return len(text) * self.size * 0.5

    def metrics(self, name):
        return self.size + 3


class OverlayRenderingTests(unittest.TestCase):
    def setUp(self):
        self.overlay = ReplacementOverlay.__new__(ReplacementOverlay)
        self.overlay.monitor = {"left": 0, "top": 0}
        self.overlay.canvas = Mock()
        self.overlay.root = Mock()
        self.overlay.hwnd = 0x123456789
        self.overlay._user32 = Mock()
        self.overlay._user32.SetWindowPos.return_value = True
        self.overlay._tkfont = SimpleNamespace(Font=PixelFont)

    def test_short_translation_keeps_the_entire_english_mask(self):
        rect = build_overlay_rect(Rect(100, 70, 470, 86), CaptureRegion(0, 0, 1190, 270))
        info = self.overlay.show_translation(rect, "Đã rõ.", cover_color="#17130f")
        self.assertEqual(info.rect, rect)
        coords = self.overlay.canvas.create_rectangle.call_args.args
        self.assertGreaterEqual(coords[3], 156)
        self.assertFalse(self.overlay.root.lift.called)
        self.assertTrue(self.overlay._user32.SetWindowPos.call_args.args[-1] & SWP_NOACTIVATE)

    def test_text_that_cannot_fit_is_hidden_instead_of_spilling_into_controls(self):
        with self.assertRaises(OverlayLayoutError):
            self.overlay._fit_text("một đoạn thoại rất dài " * 40, max_width=100, max_height=30)

    def test_long_unbroken_word_wraps_without_losing_characters(self):
        text = "PhaarylEzomyteGeneration" * 4
        font = PixelFont(size=-12)
        lines = ReplacementOverlay._wrap_pixels(text, font, 100)
        self.assertEqual("".join(lines), text)
        self.assertTrue(all(font.measure(line) <= 100 for line in lines))

    def test_native_styles_and_capture_affinity_use_the_wrapper_not_tk_child(self):
        wrapper = 0x123456789
        root, canvas, user32 = Mock(), Mock(), Mock()
        root.wm_frame.return_value = hex(wrapper)
        root.winfo_id.return_value = 123
        user32.GetAncestor.return_value = wrapper
        styles = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        user32.GetWindowLongW.side_effect = [0, styles]
        user32.SetWindowPos.return_value = True
        affinity = [0]

        def set_affinity(hwnd, value):
            self.assertEqual(hwnd, wrapper)
            affinity[0] = value
            return True

        def get_affinity(hwnd, result):
            result._obj.value = affinity[0]
            return True

        user32.SetWindowDisplayAffinity.side_effect = set_affinity
        user32.GetWindowDisplayAffinity.side_effect = get_affinity
        with patch("app.replacement_overlay.sys.platform", "win32"), \
             patch("app.replacement_overlay.sys.getwindowsversion", create=True,
                   return_value=SimpleNamespace(build=19045)), \
             patch("app.replacement_overlay.enable_per_monitor_dpi_awareness"), \
             patch("app.replacement_overlay.get_user32", return_value=user32), \
             patch.object(tkinter, "Tk", return_value=root), \
             patch.object(tkinter, "Canvas", return_value=canvas):
            overlay = ReplacementOverlay({"left": -1920, "top": 0, "width": 1920, "height": 1080})
        self.assertEqual(overlay.hwnd, wrapper)
        self.assertTrue(overlay.capture_exclusion_ok)
        self.assertEqual(user32.SetWindowLongW.call_args.args[0], wrapper)
        self.assertEqual(user32.SetWindowPos.call_args.args[2], -1920)
        self.assertTrue(root.withdraw.called)


if __name__ == "__main__":
    unittest.main()
