import unittest

from app.capture import CaptureRegion
from app.models import Rect
from app.replacement_overlay import build_overlay_rect, rgb_to_hex


class OverlayGeometryTests(unittest.TestCase):
    def test_normal_dialogue_box_translates_to_absolute_screen_pixels(self):
        region = CaptureRegion(left=230, top=421, width=1190, height=270)
        box = Rect(x=449, y=75, w=471, h=60)

        rect = build_overlay_rect(box, region)

        self.assertEqual(rect.left, 669)
        self.assertEqual(rect.top, 490)
        self.assertGreaterEqual(rect.width, 471)
        self.assertLessEqual(rect.height, 108)

    def test_overlay_stays_above_continue_safe_zone(self):
        region = CaptureRegion(left=230, top=421, width=1190, height=270)
        box = Rect(x=115, y=155, w=470, h=100)

        rect = build_overlay_rect(box, region)
        safe_bottom = region.top + round(region.height * 0.70)

        self.assertLessEqual(rect.bottom, safe_bottom)

    def test_rgb_to_hex(self):
        self.assertEqual(rgb_to_hex((23, 19, 15)), "#17130f")


if __name__ == "__main__":
    unittest.main()
