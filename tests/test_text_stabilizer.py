import unittest

from app.text_stabilizer import TextStabilizer


class TextStabilizerTests(unittest.TestCase):
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
