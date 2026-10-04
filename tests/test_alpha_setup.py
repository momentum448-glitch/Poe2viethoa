import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.translation_models import TranslationRecord
from app.translation_store import build_sqlite
from tools import alpha_setup as setup


class AlphaSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for folder in ("sources", "translations", "source_data", "runtime"):
            (self.root / folder).mkdir()
        (self.root / "requirements.txt").write_text("mss>=10,<11\n")
        lock = {"sources": {"poe2_en": {"ref": "english"}, "dialogue_context": {"ref": "context"}}}
        (self.root / "sources/sources.lock.json").write_text(json.dumps(lock))
        (self.root / "translations/dialogue_vi.json").write_text(json.dumps([
            {"source_id": "dlg_test", "vi": "Cây cầu cũ đã sập.", "status": "reviewed"}
        ]))
        (self.root / "source_data/dialogue_corpus.jsonl").write_text(json.dumps(
            {"source_id": "dlg_test", "source": "The old bridge has fallen."}) + "\n")
        (self.root / "source_data/source_sync_report.json").write_text(json.dumps(
            {"source_ref": "english", "context_ref": "context"}))
        self.target = self.root / "runtime/translations.sqlite3"
        build_sqlite([TranslationRecord("dlg_test", "Original source.", "Bản dịch cũ.", status="reviewed")], self.target)
        self.stamp()

    def stamp(self):
        (self.root / "runtime/alpha_setup.json").write_text(json.dumps({"signature": setup.signature(self.root)}))

    def prepare(self, runner):
        with patch.object(setup, "check_platform"), patch.object(setup, "dependencies_available", return_value=True):
            return setup.prepare(self.root, runner=runner)

    def test_cached_preparation_rebuilds_database_without_installing_or_downloading(self):
        runner = Mock()
        self.assertEqual(self.prepare(runner), 1)
        runner.assert_not_called()
        self.assertEqual(setup.database_count(self.root), 1)
        with patch.object(setup, "dependencies_available", return_value=True), patch.object(setup.subprocess, "run", side_effect=AssertionError("No network")):
            self.assertTrue(setup.readiness(self.root, platform_check=False)[0])

    def test_changed_translations_require_setup_even_when_database_exists(self):
        (self.root / "translations/dialogue_vi.json").write_text("[]")
        with patch.object(setup, "dependencies_available", return_value=True):
            self.assertFalse(setup.readiness(self.root, platform_check=False)[0])

    def test_corrupt_database_cannot_pass_readiness(self):
        self.target.write_bytes(b"not sqlite")
        with patch.object(setup, "dependencies_available", return_value=True):
            self.assertFalse(setup.readiness(self.root, platform_check=False)[0])

    def test_source_join_failure_preserves_existing_database(self):
        before = self.target.read_bytes()
        (self.root / "source_data/dialogue_corpus.jsonl").write_text(json.dumps(
            {"source_id": "dlg_other", "source": "A different source."}) + "\n")
        with self.assertRaises(RuntimeError):
            self.prepare(Mock())
        self.assertEqual(self.target.read_bytes(), before)

    def test_failed_database_build_preserves_existing_database_and_removes_temp(self):
        before = self.target.read_bytes()

        def failed(records, path):
            path.write_bytes(b"half-built")
            raise OSError("disk error")

        with patch.object(setup, "build_sqlite", side_effect=failed), self.assertRaises(OSError):
            self.prepare(Mock())
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(list((self.root / "runtime").glob("*.tmp")))

    def test_changed_pinned_refs_trigger_source_sync_before_build(self):
        (self.root / "source_data/source_sync_report.json").write_text("{}")
        runner = Mock()
        self.prepare(runner)
        runner.assert_called_once()
        self.assertIn("tools.source_sync", runner.call_args.args[0])
