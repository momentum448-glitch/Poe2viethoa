import unittest

from PIL import Image, ImageDraw

from app.capture import CaptureRegion, CapturedFrame, crop_frame
from app.dialogue_tracking import absolute_box, position_was_proofed, proof_key, tracking_region
from app.models import DialogueContext, Rect
from app.text_frame_guard import source_text_changed


class PopupTrackingTests(unittest.TestCase):
    def context(self, x, y):
        return DialogueContext(True, "normal_right", .99, "Una", "A story paragraph.",
                               Rect(x, y + 48, 460, 42), speaker_box=Rect(x + 210, y, 55, 22),
                               continue_box=Rect(x + 195, y + 170, 85, 20))

    def test_tracking_is_inside_the_captured_game_and_contains_all_local_anchors(self):
        viewport = CaptureRegion(-1700, 100, 1920, 1080)
        for x in (4, 700, 1400):
            for y in (4, 400, 860):
                with self.subTest(position=(x, y)):
                    context = self.context(x, y)
                    region = tracking_region(context, viewport, viewport)
                    self.assertGreaterEqual(region.left, viewport.left)
                    self.assertGreaterEqual(region.top, viewport.top)
                    self.assertLessEqual(region.right, viewport.right)
                    self.assertLessEqual(region.bottom, viewport.bottom)
                    self.assertLess(region.width * region.height, viewport.width * viewport.height / 2)
                    for box in (context.dialogue_box, context.speaker_box, context.continue_box):
                        box = absolute_box(box, viewport)
                        self.assertLessEqual(region.left, box.x)
                        self.assertLessEqual(region.top, box.y)
                        self.assertGreaterEqual(region.right, box.right)
                        self.assertGreaterEqual(region.bottom, box.bottom)

    def test_rebased_reference_does_not_report_unchanged_source_as_stale(self):
        viewport = CaptureRegion(-1700, 100, 1920, 1080)
        context = self.context(700, 400)
        image = Image.new("RGB", (1920, 1080), (16, 16, 16))
        ImageDraw.Draw(image).text((705, 450), "The old bridge has fallen.", fill=(238, 228, 201))
        frame = CapturedFrame(image.tobytes("raw", "BGRX"), 1920, 1080, viewport)
        region = tracking_region(context, viewport, viewport)
        reference = crop_frame(frame, region)
        box = context.dialogue_box.translated(viewport.left - region.left, viewport.top - region.top)
        self.assertFalse(source_text_changed(reference, crop_frame(frame, region), box))
        self.assertEqual(absolute_box(box, region), absolute_box(context.dialogue_box, viewport))

    def test_proofs_cover_new_positions_and_ignore_small_jitter_even_at_a_grid_boundary(self):
        viewport = CaptureRegion(-1700, 100, 1920, 1080)
        key = proof_key("page-a", Rect(23, 23, 460, 42), viewport)
        positions = {key}
        self.assertTrue(position_was_proofed(proof_key("page-a", Rect(24, 24, 460, 42), viewport), positions))
        self.assertFalse(position_was_proofed(proof_key("page-a", Rect(800, 650, 460, 42), viewport), positions))
        self.assertFalse(position_was_proofed(proof_key("page-b", Rect(23, 23, 460, 42), viewport), positions))
        # The same absolute position inside a tracking crop is still the same proof.
        crop = CaptureRegion(-1690, 110, 700, 400)
        self.assertTrue(position_was_proofed(proof_key("page-a", Rect(13, 13, 460, 42), crop), positions))
