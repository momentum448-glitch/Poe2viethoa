import json
import tempfile
import unittest
from pathlib import Path

from app.translation_store import build_sqlite, load_json_records, TranslationStore


class TranslationStoreTests(unittest.TestCase):
    def test_json_to_sqlite_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "dialogue.json"
            source.write_text(
                json.dumps(
                    [
                        {
                            "id": "x1",
                            "source": "A simple source line.",
                            "vi": "Một câu dịch.",
                            "speaker": "NPC",
                            "area": "Camp",
                            "type": "dialogue",
                            "status": "approved",
                            "aliases": ["A simple source llne."],
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            records = load_json_records(source)
            db = root / "runtime.sqlite3"
            build_sqlite(records, db)

            store = TranslationStore(db)
            try:
                exact = store.exact("a simple source line", speaker="NPC", area="Camp")
                self.assertIsNotNone(exact)
                alias = store.exact("a simple source llne", speaker="NPC", area="Camp")
                self.assertIsNotNone(alias)
                self.assertEqual(alias.id, "x1")
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
