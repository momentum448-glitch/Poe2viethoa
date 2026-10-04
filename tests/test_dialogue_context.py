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

    def test_expanded_capture_recovers_a_lower_dialogue_panel(self):
        lines = [
            line("Una", 860, 200, 70),
            line("The camp shelters those who have nowhere else to go.", 690, 245),
            line("We gather wood and food before the sun goes down.", 690, 275),
            line("Help us if you can, and speak to the others here.", 690, 305),
            line("Continue", 880, 374, 100),
        ]
        self.assertFalse(DialogueContextDetector(1190, 270).detect(lines).detected)
        ctx = DialogueContextDetector(1190, 486).detect(lines)
        self.assertTrue(ctx.detected)
        self.assertEqual(ctx.layout, "normal_right")
        self.assertEqual(ctx.text, " ".join(item.text for item in lines[1:4]))
        self.assertEqual(ctx.dialogue_box.bottom, 329)
        self.assertIn("continue_cue_found", ctx.reasons)

    def test_expanded_capture_still_rejects_topic_menu_and_bottom_chat(self):
        detector = DialogueContextDetector(1190, 486)
        menu = [
            line("Renly", 690, 50, 90),
            line("Introduction", 475, 103, 130),
            line("The Devourer", 840, 105, 130),
            line("Buy or Sell items", 820, 145, 200),
            line("Goodbye", 820, 190, 90),
        ]
        self.assertFalse(detector.detect(menu).detected)
        chat = [line("Someone wrote a long message in the global chat window.", 20, 425, 550)]
        self.assertFalse(detector.detect(chat).detected)


if __name__ == "__main__":
    unittest.main()
