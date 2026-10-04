import unittest

from app.dialogue_context import DialogueContextDetector
from app.models import OcrLine, Rect


def line(text, x, y, w=420, h=24):
    return OcrLine(text=text, box=Rect(x, y, w, h), words=[])


class DialogueContextDetectorTests(unittest.TestCase):
    def test_detects_normal_right_dialogue(self):
        detector = DialogueContextDetector(1200, 270)
        lines = [
            line("Renly", 620, 20, 80),
            line("I've seen what those things can do to a man.", 610, 58),
            line("We should be careful beyond the riverbank.", 612, 88),
            line("Continue", 900, 210, 100),
        ]

        ctx = detector.detect(lines)
        self.assertTrue(ctx.detected)
        self.assertEqual(ctx.layout, "normal_right")
        self.assertEqual(ctx.speaker, "Renly")
        self.assertIn("riverbank", ctx.text)

    def test_detects_inventory_left_dialogue(self):
        detector = DialogueContextDetector(1200, 270)
        lines = [
            line("Renly", 220, 25, 80),
            line("Phaaryl knows more about the Bloody Flowers.", 210, 60),
            line("Ask her before you leave Clearfell.", 212, 91),
        ]

        ctx = detector.detect(lines)
        self.assertTrue(ctx.detected)
        self.assertEqual(ctx.layout, "inventory_left")
        self.assertEqual(ctx.speaker, "Renly")

    def test_rejects_short_ui_noise(self):
        detector = DialogueContextDetector(1200, 270)
        lines = [
            line("Inventory", 100, 40, 100),
            line("Continue", 800, 150, 100),
        ]

        ctx = detector.detect(lines)
        self.assertFalse(ctx.detected)


if __name__ == "__main__":
    unittest.main()
