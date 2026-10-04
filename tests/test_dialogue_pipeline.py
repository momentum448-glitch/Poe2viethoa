import tempfile
import unittest
from pathlib import Path

from app.dialogue_pipeline import DialogueTranslationPipeline
from app.matcher import DialogueMatcher
from app.text_stabilizer import TextStabilizer
from app.translation_models import TranslationRecord
from app.translation_store import TranslationStore, build_sqlite


class DialoguePipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "translations.sqlite3"
        build_sqlite(
            [
                TranslationRecord(
                    id="x",
                    source="The old bridge has fallen.",
                    vi="Cây cầu cũ đã sập.",
                    speaker="Keeper",
                    status="approved",
                )
            ],
            db,
        )
        self.store = TranslationStore(db)
        self.pipeline = DialogueTranslationPipeline(
            DialogueMatcher(self.store),
            stabilizer=TextStabilizer(duplicate_similarity=0.94),
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_duplicate_ocr_does_not_repeat_match(self):
        first = self.pipeline.process(
            "The old bridge has fallen.",
            speaker="Keeper",
            layout="normal",
        )
        second = self.pipeline.process(
            "The old brldge has fallen.",
            speaker="Keeper",
            layout="normal",
        )

        self.assertTrue(first.emit)
        self.assertTrue(first.translation.should_display_normal)
        self.assertFalse(second.emit)
        self.assertIsNone(second.translation)


if __name__ == "__main__":
    unittest.main()
