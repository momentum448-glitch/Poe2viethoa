import unittest

from app.frame_stabilizer import FrameStabilizer


def solid_bgra(value: int, pixels: int = 100) -> bytes:
    return bytes([value, value, value, 255] * pixels)


class FrameStabilizerTests(unittest.TestCase):
    def test_waits_for_settle_after_change(self):
        s = FrameStabilizer(
            sample_stride=1,
            changed_fraction_threshold=0.01,
            stable_frames_required=2,
            min_ocr_interval_ms=0,
        )

        self.assertFalse(s.observe(solid_bgra(0), now=0.0).should_ocr)
        self.assertFalse(s.observe(solid_bgra(30), now=0.1).should_ocr)
        self.assertFalse(s.observe(solid_bgra(30), now=0.2).should_ocr)
        decision = s.observe(solid_bgra(30), now=0.3)
        self.assertTrue(decision.should_ocr)
        self.assertEqual(decision.reason, "settled")

    def test_unchanged_frame_does_not_retrigger_after_ocr(self):
        s = FrameStabilizer(
            sample_stride=1,
            changed_fraction_threshold=0.01,
            stable_frames_required=1,
            min_ocr_interval_ms=0,
        )

        s.observe(solid_bgra(0), now=0.0)
        decision = s.observe(solid_bgra(0), now=0.1)
        self.assertTrue(decision.should_ocr)
        s.mark_ocr(now=0.1)

        decision = s.observe(solid_bgra(0), now=10.0)
        self.assertFalse(decision.should_ocr)
        self.assertEqual(decision.reason, "unchanged_since_ocr")

    def test_new_change_rearms_after_ocr(self):
        s = FrameStabilizer(
            sample_stride=1,
            changed_fraction_threshold=0.01,
            stable_frames_required=1,
            min_ocr_interval_ms=0,
        )

        s.observe(solid_bgra(0), now=0.0)
        self.assertTrue(s.observe(solid_bgra(0), now=0.1).should_ocr)
        s.mark_ocr(now=0.1)

        self.assertFalse(s.observe(solid_bgra(50), now=0.2).should_ocr)
        self.assertTrue(s.observe(solid_bgra(50), now=0.3).should_ocr)


if __name__ == "__main__":
    unittest.main()
