from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.capture import ScreenCapture


class DialogueCaptureTests(unittest.TestCase):
    def region_for(self, monitor):
        with patch("app.capture.mss.mss", return_value=SimpleNamespace(monitors=[{}, monitor])):
            return ScreenCapture().default_dialogue_region()

    def test_lower_npc_paragraph_and_continue_fit_inside_capture(self):
        region = self.region_for({"left": 0, "top": 0, "width": 1920, "height": 1080})
        # A lower popup starts at the Una header seen in QC event 49; allow a
        # multi-line paragraph and its footer below the old 691px capture edge.
        for x, y, width, height in ((915, 625, 100, 26), (915, 665, 476, 120), (1150, 820, 100, 26)):
            with self.subTest(rect=(x, y, width, height)):
                self.assertLessEqual(region.left, x)
                self.assertLessEqual(region.top, y)
                self.assertGreaterEqual(region.left + region.width, x + width)
                self.assertGreaterEqual(region.top + region.height, y + height)
        self.assertLess(region.top + region.height, 970)  # bottom game HUD

    def test_lower_popup_coverage_scales_with_monitor_size_and_origin(self):
        for width, height, left, top in ((1366, 768, 0, 0), (1920, 1080, -1920, 80), (2560, 1440, 0, -1440)):
            with self.subTest(size=(width, height), origin=(left, top)):
                region = self.region_for({"left": left, "top": top, "width": width, "height": height})
                self.assertLessEqual(region.left, left + width * 0.47)
                self.assertGreaterEqual(region.left + region.width, left + width * 0.73)
                self.assertLessEqual(region.top, top + height * 0.58)
                self.assertGreaterEqual(region.top + region.height, top + height * 0.79)
                self.assertGreaterEqual(region.left, left)
                self.assertGreaterEqual(region.top, top)
                self.assertLessEqual(region.left + region.width, left + width)
                self.assertLess(region.top + region.height, top + height * 0.90)


if __name__ == "__main__":
    unittest.main()
