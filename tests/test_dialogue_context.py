import unittest

from app.dialogue_context import DialogueContextDetector
from app.models import OcrLine, OcrWord, Rect


def line(text, x, y, w=420, h=24):
    return OcrLine(text=text, box=Rect(x, y, w, h), words=[])


class DialogueContextDetectorTests(unittest.TestCase):
    def test_same_dialogue_is_detected_at_corners_edges_and_center_on_multiple_resolutions(self):
        text = ["We have sheltered here since the bridge fell.",
                "The river will be safer when the storm passes."]
        for width, height in ((1366, 768), (1920, 1080), (2560, 1440), (3840, 2160)):
            scale = height / 1080
            panel_width, panel_height = 520 * scale, 210 * scale
            for x in (4 * scale, (width - panel_width) / 2, width - panel_width - 4 * scale):
                for y in (4 * scale, (height - panel_height) / 2, height - panel_height - 4 * scale):
                    with self.subTest(resolution=(width, height), position=(x, y)):
                        lines = [line("Una", x + 210 * scale, y, 55 * scale, 22 * scale),
                                 line(text[0], x, y + 48 * scale, 460 * scale, 20 * scale),
                                 line(text[1], x, y + 70 * scale, 450 * scale, 20 * scale),
                                 line("Continue", x + 195 * scale, y + 170 * scale, 85 * scale, 20 * scale)]
                        ctx = DialogueContextDetector(width, height).detect(lines)
                        self.assertTrue(ctx.detected)
                        self.assertEqual(ctx.text, " ".join(text))
                        self.assertEqual(ctx.speaker, "Una")
                        self.assertEqual(ctx.continue_box, lines[3].box)
                        self.assertEqual(ctx.speaker_box, lines[0].box)

    def test_chat_above_and_left_of_renly_is_not_part_of_the_paragraph(self):
        # QC 070347 events 6/9/12: x=282 chat was merged into x=460 dialogue.
        lines = [line("time to gamble", 282, 33, 102, 16),
                 line("Renly", 670, 32, 59, 22),
                 line("We will shelter here until the storm passes.", 460, 88, 470, 20),
                 line("I can mend the bridge when the river falls.", 460, 110, 446, 20),
                 line("Continue", 657, 208, 79, 20)]
        ctx = DialogueContextDetector(1190, 486).detect(lines)
        self.assertTrue(ctx.detected)
        self.assertEqual(ctx.speaker, "Renly")
        self.assertEqual(ctx.source_line_indexes, [2, 3])
        self.assertEqual(ctx.dialogue_box.x, 460)
        self.assertEqual(ctx.dialogue_box.y, 88)
        self.assertNotIn("gamble", ctx.text)

    def test_arbitrary_short_chat_cannot_replace_finn_as_the_speaker(self):
        lines = [line("Finn", 271, 119, 43, 22),
                 line("what", 0, 147, 38, 16),
                 line("The bridge is gone and our supplies are low.", 56, 174, 470, 20),
                 line("We must find another way across the river.", 56, 196, 450, 20),
                 line("Continue", 252, 307, 80, 20)]
        ctx = DialogueContextDetector(1190, 486).detect(lines)
        self.assertEqual(ctx.speaker, "Finn")
        self.assertNotIn("what", ctx.text)
        ctx = DialogueContextDetector(1190, 486).detect(lines[1:])
        self.assertTrue(ctx.detected)  # local footer still anchors the body
        self.assertIsNone(ctx.speaker)

    def test_word_geometry_splits_a_chat_line_joined_to_dialogue_by_ocr(self):
        words = [OcrWord("chat", Rect(10, 80, 35, 20)),
                 OcrWord("from", Rect(48, 80, 35, 20)),
                 OcrWord("players", Rect(86, 80, 55, 20))]
        x = 450
        for text in "The old bridge has fallen.".split():
            words.append(OcrWord(text, Rect(x, 80, len(text) * 8, 20)))
            x += len(text) * 8 + 8
        lines = [line("Renly", 620, 30, 65, 22),
                 OcrLine("chat from players The old bridge has fallen.", Rect(10, 80, x - 10, 20), words),
                 line("Continue", 620, 160, 80, 20)]
        ctx = DialogueContextDetector(1920, 1080).detect(lines)
        self.assertTrue(ctx.detected)
        self.assertEqual(ctx.text, "The old bridge has fallen.")
        self.assertEqual(ctx.dialogue_box.x, 450)

    def test_interleaved_ocr_order_does_not_split_the_correct_column(self):
        lines = [line("Renly", 700, 40, 80, 22),
                 line("We have sheltered here since the bridge fell.", 500, 90, 460, 20),
                 line("Anyone wants to trade some spare equipment?", 20, 104, 390, 16),
                 line("The river will be safer when the storm passes.", 500, 112, 465, 20),
                 line("Continue", 700, 200, 80, 20)]
        ctx = DialogueContextDetector(1920, 1080).detect(lines)
        self.assertEqual(ctx.source_line_indexes, [1, 3])
        self.assertNotIn("equipment", ctx.text)

    def test_an_outlier_word_height_does_not_leave_the_first_or_last_english_line_outside_the_mask(self):
        first = "We have sheltered here since the bridge fell."
        last = "The river will be safer when the storm passes."
        words = []
        x = 450
        for i, text in enumerate(first.split()):
            box = Rect(x, 79 if i == 0 else 88, len(text) * 8, 42 if i == 0 else 20)
            words.append(OcrWord(text, box))
            x += len(text) * 8 + 8
        lines = [line("Renly", 650, 32, 70, 24),
                 OcrLine(first, Rect(450, 79, x - 450, 42), words),
                 line(last, 450, 110, 430, 20),
                 line("Continue", 650, 208, 80, 20)]
        ctx = DialogueContextDetector(1920, 1080).detect(lines)
        self.assertEqual(ctx.text, first + " " + last)
        self.assertEqual(ctx.source_line_indexes, [1, 2])
        self.assertLessEqual(ctx.dialogue_box.y, 88)
        self.assertGreaterEqual(ctx.dialogue_box.bottom, 130)

    def test_hooded_one_header_is_not_mistaken_for_a_sentence(self):
        lines = [line("The Hooded One", 170, 20, 150, 22),
                 line("The river will be safer when the storm passes.", 40, 70, 440, 20),
                 line("Continue", 195, 150, 90, 20)]
        ctx = DialogueContextDetector(1920, 1080).detect(lines)
        self.assertEqual(ctx.speaker, "The Hooded One")
        self.assertEqual(ctx.source_line_indexes, [1])

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
        self.assertEqual(ctx.speaker, "Una")
        self.assertIn("continue_cue_found", ctx.reasons)

    def test_chat_does_not_steal_continue_from_a_lower_una_popup(self):
        # Alpha.2 QC event 20: the longer chat line at x=7/y=316 won the
        # sentence score, even though Una and Continue belonged to the right panel.
        dialogue = "In many ways, he reminds me of my father..."
        chat = "i needs* uncut skill gems level 13 and 5x uncut skill gems -level '4;"
        lines = [
            line("Una", 885, 202, 45, 22),
            line(dialogue, 672, 258, 384, 20),
            line("that corruption", 0, 297, 110, 16),
            line(chat, 7, 316, 441, 16),
            line("Continue", 868, 378, 80, 20),
        ]
        ctx = DialogueContextDetector(1190, 486).detect(lines)
        self.assertTrue(ctx.detected)
        self.assertEqual(ctx.text, dialogue)
        self.assertEqual(ctx.speaker, "Una")
        self.assertEqual(ctx.layout, "normal_right")
        self.assertEqual(ctx.source_line_indexes, [1])

    def test_continue_from_another_column_cannot_anchor_chat(self):
        lines = [
            line("that corruption", 0, 297, 110, 16),
            line("I need uncut skill gems level thirteen and fourteen.", 7, 316, 441, 16),
            line("Continue", 868, 378, 80, 20),
        ]
        ctx = DialogueContextDetector(1190, 486).detect(lines)
        self.assertFalse(ctx.detected)
        self.assertIn("no_dialogue_anchor", ctx.reasons)

    def test_continue_above_the_paragraph_is_not_an_anchor(self):
        lines = [
            line("Continue", 868, 200, 80, 20),
            line("We should be careful beyond the riverbank.", 672, 258),
        ]
        self.assertFalse(DialogueContextDetector(1190, 486).detect(lines).detected)

    def test_distant_continue_is_not_an_anchor(self):
        lines = [
            line("We should be careful beyond the riverbank.", 672, 30),
            line("Continue", 868, 378, 80, 20),
        ]
        self.assertFalse(DialogueContextDetector(1190, 486).detect(lines).detected)

    def test_local_continue_still_works_when_the_speaker_is_missing(self):
        lines = [
            line("We should be careful beyond the riverbank.", 672, 258),
            line("Continue", 868, 378, 80, 20),
        ]
        ctx = DialogueContextDetector(1190, 486).detect(lines)
        self.assertTrue(ctx.detected)
        self.assertEqual(ctx.text, lines[0].text)
        self.assertIsNone(ctx.speaker)
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
