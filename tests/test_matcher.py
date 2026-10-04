import tempfile
import unittest
from pathlib import Path

from app.matcher import DialogueMatcher
from app.translation_models import TranslationRecord
from app.translation_store import TranslationStore, build_sqlite


class MatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "translations.sqlite3"
        build_sqlite(
            [
                TranslationRecord(
                    id="a",
                    source="The old bridge has fallen.",
                    vi="Cây cầu cũ đã sập.",
                    speaker="Keeper",
                    area="Camp",
                    status="approved",
                ),
                TranslationRecord(
                    id="b",
                    source="The road ahead is clear.",
                    vi="Con đường phía trước đã thông.",
                    speaker="Keeper",
                    area="Camp",
                    status="reviewed",
                ),
                TranslationRecord(
                    id="c",
                    source="The road ahead is near.",
                    vi="Con đường phía trước đã gần.",
                    status="approved",
                ),
                TranslationRecord(
                    id="draft",
                    source="This draft must stay hidden.",
                    vi="Bản nháp.",
                    status="draft",
                ),
            ],
            self.db_path,
        )
        self.store = TranslationStore(self.db_path)
        self.matcher = DialogueMatcher(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_exact_match(self):
        r = self.matcher.match(
            "The old bridge has fallen.",
            speaker="Keeper",
            area="Camp",
        )
        self.assertTrue(r.matched)
        self.assertEqual(r.method, "exact")
        self.assertEqual(r.confidence, "high")
        self.assertTrue(r.should_display_normal)

    def test_fuzzy_ocr_typo(self):
        r = self.matcher.match(
            "The old brldge has fallen.",
            speaker="Keeper",
            area="Camp",
        )
        self.assertTrue(r.matched)
        self.assertEqual(r.confidence, "high")
        self.assertEqual(r.record.id, "a")

    def test_ambiguous_fuzzy_high_score_is_hidden_in_normal_mode(self):
        r = self.matcher.match("The road ahead is cear.")
        self.assertTrue(r.matched)
        self.assertEqual(r.confidence, "medium")
        self.assertFalse(r.should_display_normal)
        self.assertEqual(r.record.id, "b")
        self.assertGreaterEqual(len(r.candidates), 2)

    def test_draft_not_visible(self):
        r = self.matcher.match("This draft must stay hidden.")
        self.assertFalse(r.matched)

    def test_wrong_speaker_filters_candidate(self):
        r = self.matcher.match(
            "The old bridge has fallen.",
            speaker="SomeoneElse",
            area="Camp",
        )
        self.assertFalse(r.matched)


if __name__ == "__main__":
    unittest.main()
