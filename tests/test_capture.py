from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

from app.capture import CaptureRegion, CapturedFrame, ScreenCapture, crop_frame


class DialogueCaptureTests(unittest.TestCase):
    def capture_for(self, desktop):
        with patch("app.capture.mss.mss", return_value=SimpleNamespace(monitors=[desktop, desktop])):
            return ScreenCapture()

    def test_discovery_covers_the_entire_game_including_all_four_corners(self):
        for width, height, left, top in ((1366, 768, 0, 0), (1920, 1080, -1920, 80),
                                         (2560, 1440, 0, -1440)):
            with self.subTest(size=(width, height), origin=(left, top)):
                client = CaptureRegion(left, top, width, height)
                capture = self.capture_for(client.as_mss())
                self.assertEqual(capture.game_region(client), client)
                self.assertEqual(capture.desktop_monitor(), client.as_mss())

    def test_windowed_discovery_does_not_include_the_surrounding_desktop(self):
        desktop = CaptureRegion(-1920, -200, 3840, 1280)
        capture = self.capture_for(desktop.as_mss())
        client = CaptureRegion(250, 130, 1280, 720)
        self.assertEqual(capture.game_region(client), client)
        self.assertEqual(capture.game_region(CaptureRegion(-2000, 0, 900, 700)),
                         CaptureRegion(-1920, 0, 820, 700))

    def test_unknown_minimized_and_offscreen_client_bounds_never_fall_back_to_screen(self):
        capture = self.capture_for(CaptureRegion(0, 0, 1920, 1080).as_mss())
        for client in (None, CaptureRegion(0, 0, 0, 0), CaptureRegion(2000, 0, 1280, 720)):
            self.assertIsNone(capture.game_region(client))

    def test_tracking_reference_crop_keeps_the_exact_bgra_pixels_and_origin(self):
        pixels = bytes(range(128))
        original = CapturedFrame(pixels, 8, 4, CaptureRegion(-1920, 80, 8, 4))
        region = CaptureRegion(-1918, 81, 4, 2)
        cropped = crop_frame(original, region)
        expected = b"".join(pixels[start:start + 16] for start in (40, 72))
        self.assertEqual(cropped.bgra, expected)
        self.assertEqual((cropped.width, cropped.height, cropped.region), (4, 2, region))
        self.assertIs(crop_frame(original, original.region), original)
        with self.assertRaises(ValueError):
            crop_frame(original, CaptureRegion(-1921, 80, 8, 4))


if __name__ == "__main__":
    unittest.main()
