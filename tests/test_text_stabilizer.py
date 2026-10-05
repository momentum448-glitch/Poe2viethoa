import unittest

from app.text_stabilizer import TextStabilizer


class TextStabilizerTests(unittest.TestCase):
    def test_same_page_reemits_when_it_moves_within_the_same_layout(self):
        s = TextStabilizer()
        s.observe("The old bridge has fallen.", speaker="A", layout="normal",
                  position=(1100, 300), now=0)
        moved = s.observe("The old bridge has fallen.", speaker="A", layout="normal",
                          position=(1400, 700), now=1)
        self.assertTrue(moved.emit)
        self.assertEqual(moved.reason, "context_changed")

    def test_position_jitter_keeps_deduplication_until_the_anchor_has_moved(self):
        s = TextStabilizer()
        s.observe("The old bridge has fallen.", position=(100, 100), now=0)
        for x in (101, 102, 106):
            self.assertFalse(s.observe("The old bridge has fallen.", position=(x, 101), now=1).emit)
        self.assertTrue(s.observe("The old bridge has fallen.", position=(110, 101), now=2).emit)

    def test_first_text_emits(self):
        s = TextStabilizer()
        d = s.observe("The old bridge has fallen.", speaker="A", layout="normal", now=0)
        self.assertTrue(d.emit)

    def test_near_identical_ocr_is_suppressed(self):
        s = TextStabilizer(duplicate_similarity=0.94)
        self.assertTrue(
            s.observe(
                "The old bridge has fallen.",
                speaker="A",
                layout="normal",
                now=0,
            ).emit
        )
        d = s.observe(
            "The old brldge has fallen.",
            speaker="A",
            layout="normal",
            now=1,
        )
        self.assertFalse(d.emit)
        self.assertEqual(d.reason, "duplicate")

    def test_changed_text_emits(self):
        s = TextStabilizer()
        s.observe("The old bridge has fallen.", speaker="A", layout="normal", now=0)
        d = s.observe(
            "The road ahead is clear.",
            speaker="A",
            layout="normal",
            now=1,
        )
        self.assertTrue(d.emit)

    def test_context_change_emits(self):
        s = TextStabilizer()
        s.observe("Stay close.", speaker="A", layout="normal", now=0)
        d = s.observe("Stay close.", speaker="B", layout="normal", now=1)
        self.assertTrue(d.emit)
        self.assertEqual(d.reason, "context_changed")


if __name__ == "__main__":
    unittest.main()
