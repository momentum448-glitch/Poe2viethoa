import json
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from app.translation_store import compile_translation_records, load_vi_entries
from tools.build_translation_db import build_database
from tools.translation_factory import (
    approve, atomic_json, mark_reviewed, prepare, publish, qa, render_bundle,
    select_qc, text_sha,
)


class TranslationFactoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.catalog_path = self.root / "translations/dialogue_vi.json"
        self.corpus_path = self.root / "source_data/dialogue_corpus.jsonl"
        self.rows = [
            {"source_id": "one", "source": "Renly protects these people.", "speaker": "Una",
             "topic": "Renly", "segment_index": 0, "segment_count": 2},
            {"source_id": "two", "source": "He reminds me of my father...", "speaker": "Una",
             "topic": "Renly", "segment_index": 1, "segment_count": 2},
            {"source_id": "memory", "source": "Renly brings hope.", "speaker": "Una", "topic": "Home"},
        ]
        for row in self.rows:
            row.update(source_snapshot="source-pin", context_snapshot="context-pin")
        self.write_corpus()
        atomic_json(self.root / "sources/sources.lock.json", {
            "sources": {"poe2_en": {"ref": "source-pin"}, "dialogue_context": {"ref": "context-pin"}}})
        atomic_json(self.root / "translations/glossary.json",
                    {"schema": 1, "terms": [{"source": "Renly", "target": "Renly"}],
                     "style": ["Giữ nghĩa và tên riêng."]})
        atomic_json(self.catalog_path, [{"source_id": "memory", "vi": "Renly mang lại hy vọng.",
                                         "status": "reviewed"}])

    def write_corpus(self):
        self.corpus_path.parent.mkdir(parents=True, exist_ok=True)
        self.corpus_path.write_text("\n".join(json.dumps(r) for r in self.rows) + "\n", encoding="utf-8")

    def batch(self, *ids):
        path = self.root / f"batch-{len(list(self.root.glob('batch-*')))}.json"
        result = prepare(self.root, list(ids or ["one"]), "test-batch", path)
        texts = {"one": "Renly bảo vệ những người này.", "two": "Ông ấy khiến tôi nhớ đến cha..."}
        for entry in result["entries"]:
            entry["vi"] = texts.get(entry["source_id"], "Một bản dịch mới.")
        return result

    def reviewed(self, *ids):
        return mark_reviewed(self.root, self.batch(*ids), "AI_test", "Đã soát nghĩa với các trang cùng chủ đề.")

    def codes(self, batch):
        return {i["code"] for i in qa(self.root, batch)["issues"]}

    def test_qc_selection_accepts_exact_source_but_rejects_chat_and_ambiguity(self):
        events = []
        for n, text in enumerate([self.rows[0]["source"], "Trade chat selling gems.", self.rows[0]["source"]]):
            events.append({"event": n, "dialogue": {"detected": True, "text": text, "speaker": "Una"},
                           "pipeline": {"emit": True, "translation": {"matched": False}}})
        archive = self.root / "qc.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("events.jsonl", "\n".join(json.dumps(e) for e in events))
        selected, unresolved = select_qc(self.root, archive)
        self.assertEqual(selected, ["one"])
        self.assertEqual(unresolved, ["1"])
        self.rows.append({**self.rows[0], "source_id": "ambiguous"})
        self.write_corpus()
        self.assertEqual(select_qc(self.root, archive)[0], [])

    def test_draft_qa_pass_does_not_publish_without_semantic_review(self):
        batch = self.batch()
        before = self.catalog_path.read_bytes()
        self.assertTrue(qa(self.root, batch)["passed"])
        with self.assertRaises(ValueError):
            publish(self.root, batch)
        self.assertEqual(self.catalog_path.read_bytes(), before)

    def test_source_or_glossary_changes_block_a_reviewed_batch(self):
        batch = self.reviewed()
        self.rows[0]["source"] += " Today."
        self.write_corpus()
        self.assertIn("changed_source", self.codes(batch))
        with self.assertRaises(ValueError):
            publish(self.root, batch)
        atomic_json(self.root / "translations/glossary.json", {"schema": 1, "terms": []})
        self.assertIn("stale_glossary_sha256", self.codes(batch))

    def test_review_digest_detects_a_later_vietnamese_edit(self):
        batch = self.reviewed()
        batch["entries"][0]["vi"] += " Không có trong nguồn."
        self.assertIn("edited_after_review", self.codes(batch))
        before = self.catalog_path.read_bytes()
        with self.assertRaises(ValueError):
            publish(self.root, batch)
        self.assertEqual(self.catalog_path.read_bytes(), before)

    def test_glossary_numbers_and_placeholders_are_enforced(self):
        self.rows[0]["source"] = "Renly needs {count} keys and 2 gems."
        self.write_corpus()
        batch = self.batch()
        batch["entries"][0]["vi"] = "Ông ấy cần chìa khóa và 3 viên ngọc."
        self.assertTrue({"glossary", "numbers", "placeholders"} <= self.codes(batch))
        batch["entries"][0]["vi"] = "Renly cần {count} chìa khóa và 2 viên ngọc."
        self.assertTrue(qa(self.root, batch)["passed"])

    def test_duplicate_or_invalid_state_cannot_enter_runtime(self):
        batch = self.batch()
        batch["entries"].append(dict(batch["entries"][0]))
        self.assertIn("duplicate_source", self.codes(batch))
        batch["entries"] = batch["entries"][:1]
        batch["entries"][0]["status"] = "unknown"
        with self.assertRaises(ValueError):
            mark_reviewed(self.root, batch, "AI", "Đã soát nghĩa.")

    def test_publish_is_idempotent_and_preserves_existing_reviewed_work(self):
        batch = self.reviewed("one", "two")
        original = load_vi_entries(self.catalog_path)[0]
        self.assertEqual(publish(self.root, batch)["changed"], 2)
        self.assertEqual(load_vi_entries(self.catalog_path)[0], original)
        with patch("tools.translation_factory.atomic_json") as writer:
            self.assertEqual(publish(self.root, batch)["changed"], 0)
            writer.assert_not_called()

    def test_catalog_conflict_fails_before_any_entry_is_written(self):
        batch = self.reviewed("one", "two")
        entries = load_vi_entries(self.catalog_path)
        entries.append({"source_id": "two", "vi": "Bản dịch từ lô khác.", "status": "reviewed"})
        atomic_json(self.catalog_path, entries)
        before = self.catalog_path.read_bytes()
        with self.assertRaises(ValueError):
            publish(self.root, batch)
        self.assertEqual(self.catalog_path.read_bytes(), before)

    def test_failed_atomic_catalog_write_preserves_original_and_cleans_temp(self):
        batch = self.reviewed()
        before = self.catalog_path.read_bytes()
        with patch.object(Path, "replace", side_effect=OSError("File locked")):
            with self.assertRaises(OSError):
                publish(self.root, batch)
        self.assertEqual(self.catalog_path.read_bytes(), before)
        self.assertEqual(list(self.catalog_path.parent.glob("*.tmp")), [])

    def test_approval_requires_review_and_cannot_be_downgraded(self):
        with self.assertRaises(ValueError):
            approve(self.root, self.batch(), "human_QC", "Đã đọc và chơi.")
        batch = approve(self.root, self.reviewed(), "human_QC", "Đã đọc và chơi.")
        self.assertTrue(qa(self.root, batch)["passed"])
        publish(self.root, batch)
        change = self.reviewed("one")
        change["entries"][0]["vi"] = "Renly che chở cho những người này."
        change = mark_reviewed(self.root, change, "AI", "Đã soát lại câu mới.")
        before = self.catalog_path.read_bytes()
        with self.assertRaises(ValueError):
            publish(self.root, change)
        self.assertEqual(self.catalog_path.read_bytes(), before)

    def test_published_reviewed_batch_can_be_promoted_after_human_qc(self):
        reviewed = self.reviewed()
        publish(self.root, reviewed)
        approved = approve(self.root, reviewed, "human_QC", "Đã QC bản phát hành trong game.")
        self.assertEqual(publish(self.root, approved)["changed"], 1)
        self.assertEqual(load_vi_entries(self.catalog_path)[-1]["status"], "approved")
        self.assertEqual(publish(self.root, reviewed)["changed"], 0)
        self.assertEqual(load_vi_entries(self.catalog_path)[-1]["status"], "approved")

    def test_corpus_from_the_wrong_snapshot_is_rejected_before_drafting(self):
        self.rows[0]["source_snapshot"] = "older-source"
        self.write_corpus()
        with self.assertRaisesRegex(ValueError, "Corpus khác nguồn"):
            self.batch()

    def test_changed_page_context_invalidates_review(self):
        batch = self.reviewed()
        batch["entries"][0]["segment_index"] = 99
        self.assertTrue({"changed_context", "edited_after_review"} <= self.codes(batch))

    def test_prompt_contains_context_and_memory_without_filling_a_draft(self):
        batch = self.batch()
        batch["entries"][0]["vi"] = ""
        report = render_bundle(self.root, batch)
        self.assertIn(self.rows[1]["source"], report)
        self.assertIn("Renly mang lại hy vọng.", report)
        self.assertEqual(batch["entries"][0]["vi"], "")

    def test_existing_batch_is_never_overwritten_by_prepare(self):
        path = self.root / "batch.json"
        atomic_json(path, {"my_work": "keep"})
        with self.assertRaises(ValueError):
            prepare(self.root, ["one"], "test", path)
        self.assertEqual(json.loads(path.read_text()), {"my_work": "keep"})

    def test_published_hashes_block_unreviewed_runtime_edits(self):
        publish(self.root, self.reviewed())
        records, _ = compile_translation_records(self.corpus_path, self.catalog_path)
        self.assertEqual(len(records), 2)
        entries = load_vi_entries(self.catalog_path)
        entries[-1]["vi"] += " Thêm ý."
        atomic_json(self.catalog_path, entries)
        with self.assertRaisesRegex(ValueError, "Vietnamese text changed"):
            compile_translation_records(self.corpus_path, self.catalog_path)

    def test_stale_source_preserves_an_existing_runtime_database(self):
        publish(self.root, self.reviewed())
        self.rows[0]["source"] += " Source changed."
        self.write_corpus()
        target = self.root / "runtime.sqlite3"
        target.write_bytes(b"old runtime")
        with self.assertRaisesRegex(ValueError, "Source changed"):
            build_database(self.corpus_path, self.catalog_path, target)
        self.assertEqual(target.read_bytes(), b"old runtime")

    def test_database_build_failure_never_replaces_a_working_runtime(self):
        publish(self.root, self.reviewed())
        target = self.root / "runtime.sqlite3"
        target.write_bytes(b"old runtime")
        def fail(records, path):
            path.write_bytes(b"partial database")
            raise RuntimeError("Build failed")
        with patch("tools.build_translation_db.build_sqlite", side_effect=fail):
            with self.assertRaises(RuntimeError):
                build_database(self.corpus_path, self.catalog_path, target)
        self.assertEqual(target.read_bytes(), b"old runtime")
        self.assertEqual(list(self.root.glob("*.tmp")), [])

    def test_malformed_catalog_never_replaces_an_existing_database(self):
        target = self.root / "runtime.sqlite3"
        target.write_bytes(b"old runtime")
        record = {"source_id": "one", "vi": "Renly bảo vệ mọi người.", "status": "reviewed"}
        for bad in ([record, record], [{**record, "status": "unknown"}], [record, "broken"]):
            with self.subTest(catalog=bad):
                atomic_json(self.catalog_path, bad)
                with self.assertRaises(ValueError):
                    build_database(self.corpus_path, self.catalog_path, target)
                self.assertEqual(target.read_bytes(), b"old runtime")

    def test_cli_qa_and_publish_exit_codes_follow_review_state(self):
        batch = self.batch()
        path = self.root / "cli-batch.json"
        atomic_json(path, batch)
        prefix = [sys.executable, "-X", "utf8", "-m", "tools.translation_factory", "--root", str(self.root)]
        def command(name, *extra):
            return subprocess.run([*prefix, name, "--batch", str(path), *extra],
                                  capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(command("qa").returncode, 0)
        self.assertEqual(command("publish").returncode, 2)
        self.assertEqual(command("mark-reviewed", "--reviewer", "AI_test", "--note", "Soát nghĩa.").returncode, 0)
        self.assertEqual(command("publish").returncode, 0)
        edited = json.loads(path.read_text(encoding="utf-8"))
        edited["entries"][0]["vi"] += " Renly nói thêm."
        atomic_json(path, edited)
        self.assertEqual(command("qa").returncode, 1)


if __name__ == "__main__":
    unittest.main()
