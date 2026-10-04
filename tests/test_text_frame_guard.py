import unittest
from PIL import Image, ImageDraw

from app.capture import CapturedFrame, CaptureRegion
from app.models import Rect
from app.text_frame_guard import source_text_changed


class TextFrameGuardTests(unittest.TestCase):
    region = CaptureRegion(230, 421, 240, 100)
    box = Rect(12, 10, 200, 50)

    def frame(self, text="The road is dangerous.", *, background=(16, 14, 12), blue=False):
        image = Image.new("RGB", (240, 100), background)
        draw = ImageDraw.Draw(image)
        if text:
            draw.text((14, 12), text, fill=(238, 228, 201))
        if blue:
            draw.rectangle((12, 25, 210, 58), fill=(140, 150, 255))
        return CapturedFrame(image.tobytes("raw", "BGRX"), 240, 100, self.region)

    def test_changed_or_closed_page_is_detected(self):
        old = self.frame()
        self.assertTrue(source_text_changed(old, self.frame("We must defeat the Count!"), self.box))
        self.assertTrue(source_text_changed(old, self.frame(""), self.box))

    def test_unchanged_glyphs_ignore_dark_world_animation_and_blue_effects(self):
        old = self.frame()
        self.assertFalse(source_text_changed(old, self.frame(background=(95, 70, 50)), self.box))
        self.assertFalse(source_text_changed(old, self.frame(blue=True), self.box))

    def test_geometry_change_invalidates_the_reference(self):
        old = self.frame()
        moved = CapturedFrame(old.bgra, old.width, old.height, CaptureRegion(231, 421, 240, 100))
        self.assertTrue(source_text_changed(old, moved, self.box))

    def test_one_bright_particle_is_not_a_dialogue_transition(self):
        old = self.frame("")
        image = Image.new("RGB", (240, 100), (16, 14, 12))
        ImageDraw.Draw(image).rectangle((30, 30, 32, 32), fill=(250, 230, 180))
        new = CapturedFrame(image.tobytes("raw", "BGRX"), 240, 100, self.region)
        self.assertFalse(source_text_changed(old, new, self.box))


if __name__ == "__main__":
    unittest.main()
