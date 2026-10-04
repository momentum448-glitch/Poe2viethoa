import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.source_sync import source_id
from tools.translation_factory import atomic_json, mark_reviewed, pins, publish, qa, render_bundle, text_sha
from tools.translation_pack import coverage, prepare_pack, validate_manifest


class TranslationPackTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "translations/batches"
        self.texts = ["The road is dangerous.", "The Seed grows in the forest.", "Bring the Seed back to me."]
        self.ids = [source_id("NPCTextAudio", text) for text in self.texts]
        groups = [(101, "First", [0, 1]), (102, "Second", [0, 2])]
        rows = []
        for i, text in enumerate(self.texts):
            rows.append({"source_id": self.ids[i], "source": text, "source_table": "NPCTextAudio",
                         "upstream_index": 101 if i < 2 else 102, "speaker": "Una",
                         "topic": "First" if i < 2 else "Second", "segment_index": 0 if i == 0 else 1,
                         "segment_count": 2, "source_snapshot": "pin", "context_snapshot": "context"})
        path = self.root / "source_data/dialogue_corpus.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        atomic_json(self.root / "sources/sources.lock.json", {"sources": {
            "poe2_en": {"ref": "pin", "files": ["dictionary/tables/NPCTextAudio.json"]},
            "dialogue_context": {"ref": "context"}}})
        atomic_json(self.root / "translations/glossary.json", {"schema": 1, "terms": []})
        atomic_json(self.root / "translations/dialogue_vi.json", [])
        raw, selected = [], []
        for index, topic, indices in groups:
            text = "<continue>".join(self.texts[i] for i in indices)
            raw.append({"index": index, "columns": {"Text": [{"en": text}]}})
            selected.append({"speaker": "Una", "topic": topic, "source_table": "NPCTextAudio",
                             "upstream_index": index, "source_sha256": text_sha(text),
                             "page_ids": [self.ids[i] for i in indices]})
        atomic_json(self.root / "source_data/cache/pin-NPCTextAudio.json", {"entries": raw})
        self.manifest = {"schema": 1, "manifest_id": "act1-test", **{k: v for k, v in pins(self.root).items() if k == "source_lock_sha256"},
                         "groups": selected, "baseline_ids": [], "style": ["Keep uncertainty."],
                         "entries": [{"source_id": sid, "source_sha256": text_sha(text)} for sid, text in zip(self.ids, self.texts)],
                         "terms": [{"source": "Seed", "target": "Hạt Giống"}]}
        self.save_manifest()

    def save_manifest(self):
        atomic_json(self.root / "translations/manifests/test.json", self.manifest)

    def test_shared_page_is_kept_in_both_source_groups_but_translated_once(self):
        report = prepare_pack(self.root, self.manifest, self.output, size=2)
        self.assertEqual([b["pages"] for b in report["batches"]], [2, 1])
        batches = [json.loads(Path(b["path"]).read_text()) for b in report["batches"]]
        ids = [e["source_id"] for b in batches for e in b["entries"]]
        self.assertEqual(ids, self.ids)
        bundle = render_bundle(self.root, batches[0])
        self.assertIn("upstream 102", bundle)
        self.assertIn(self.texts[2], bundle)
        self.assertEqual(coverage(self.root, self.manifest)["complete_groups"], 0)

    def test_missing_reused_page_reordered_pages_and_context_drift_are_rejected(self):
        for edit in (lambda m: m["groups"][1]["page_ids"].pop(0),
                     lambda m: m["groups"][0]["page_ids"].reverse(),
                     lambda m: m["groups"][1].update(speaker="Finn"),
                     lambda m: m["groups"][0].update(source_sha256="changed")):
            manifest = copy.deepcopy(self.manifest)
            edit(manifest)
            with self.subTest(manifest=manifest["groups"]), self.assertRaises(ValueError):
                validate_manifest(self.root, manifest)

    def test_topic_larger_than_batch_fails_before_creating_partial_work(self):
        with self.assertRaises(ValueError):
            prepare_pack(self.root, self.manifest, self.output, size=1)
        self.assertFalse(self.output.exists())

    def test_resume_after_publishing_keeps_batch_layout_and_review(self):
        initial = prepare_pack(self.root, self.manifest, self.output, size=2)
        path = Path(initial["batches"][0]["path"])
        batch = json.loads(path.read_text())
        for entry in batch["entries"]:
            entry["vi"] = "Hạt Giống đang phát triển." if entry["source_id"] == self.ids[1] else "Con đường nguy hiểm."
        batch = mark_reviewed(self.root, batch, "AI test", "Soát đủ hai trang.")
        atomic_json(path, batch)
        publish(self.root, batch)
        before = path.read_bytes()
        resumed = prepare_pack(self.root, self.manifest, self.output, size=2)
        self.assertEqual([b["path"] for b in initial["batches"]], [b["path"] for b in resumed["batches"]])
        self.assertTrue(all(b["state"] == "resumed" for b in resumed["batches"]))
        self.assertEqual(path.read_bytes(), before)
        report = coverage(self.root, self.manifest)
        self.assertEqual((report["displayable"], report["complete_groups"]), (2, 1))

    def test_pack_terms_and_manifest_edits_block_review_and_resume(self):
        report = prepare_pack(self.root, self.manifest, self.output, size=3)
        path = Path(report["batches"][0]["path"])
        batch = json.loads(path.read_text())
        for entry in batch["entries"]:
            entry["vi"] = "Một lời thoại đã dịch."
        self.assertIn("glossary", {i["code"] for i in qa(self.root, batch)["issues"]})
        self.manifest["style"].append("New voice constraint.")
        self.save_manifest()
        self.assertIn("changed_manifest", {i["code"] for i in qa(self.root, batch)["issues"]})
        with self.assertRaises(ValueError):
            prepare_pack(self.root, self.manifest, self.output, size=3)

    def test_topic_filter_uses_distinct_batch_name_and_baseline_is_not_retranslated(self):
        self.manifest["baseline_ids"] = [self.ids[0]]
        self.save_manifest()
        full = prepare_pack(self.root, self.manifest, self.output, size=2)
        filtered = prepare_pack(self.root, self.manifest, self.output, size=2, topics=["Second"])
        self.assertEqual(full["selected_pages"], 2)
        self.assertEqual(filtered["selected_pages"], 1)
        self.assertNotEqual(full["batches"][0]["path"], filtered["batches"][0]["path"])


if __name__ == "__main__":
    unittest.main()
