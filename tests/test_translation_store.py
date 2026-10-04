import json
import tempfile
import unittest
from pathlib import Path

from app.translation_store import (
    TranslationStore,
    build_sqlite,
    compile_translation_records,
)


class TranslationStoreTests(unittest.TestCase):
    def test_local_source_and_vi_translation_join(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            corpus = root / "dialogue_corpus.jsonl"
            corpus.write_text(
                json.dumps(
                    {
                        "source_id": "dlg_test_001",
                        "source": "A simple source line.",
                        "speaker": "NPC",
                        "area": "Camp",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            vi = root / "dialogue_vi.json"
            vi.write_text(
                json.dumps(
                    [
                        {
                            "source_id": "dlg_test_001",
                            "vi": "Một câu dịch.",
                            "status": "approved",
                            "aliases": ["A simple source llne."],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            records, stats = compile_translation_records(corpus, vi)
            self.assertEqual(stats["compiled_records"], 1)
            self.assertEqual(stats["missing_source"], 0)

            db = root / "runtime.sqlite3"
            build_sqlite(records, db)

            store = TranslationStore(db)
            try:
                exact = store.exact(
                    "a simple source line",
                    speaker="NPC",
                    area="Camp",
                )
                self.assertIsNotNone(exact)
                alias = store.exact(
                    "a simple source llne",
                    speaker="NPC",
                    area="Camp",
                )
                self.assertIsNotNone(alias)
                self.assertEqual(alias.id, "dlg_test_001")
            finally:
                store.close()

    def test_missing_source_is_reported_not_silently_built(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            corpus = root / "dialogue_corpus.jsonl"
            corpus.write_text("", encoding="utf-8")

            vi = root / "dialogue_vi.json"
            vi.write_text(
                json.dumps(
                    [
                        {
                            "source_id": "not_in_corpus",
                            "vi": "Không được build.",
                            "status": "reviewed",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            records, stats = compile_translation_records(corpus, vi)
            self.assertEqual(records, [])
            self.assertEqual(stats["missing_source"], 1)


if __name__ == "__main__":
    unittest.main()
