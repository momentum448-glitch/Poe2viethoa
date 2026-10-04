import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from app.runtime_lock import RuntimeLock
from tools.result_cleanup import apply_cleanup, pin_result, plan_cleanup


class ResultCleanupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "results").mkdir()
        self.archives = [self.archive(i) for i in range(1, 10)]

    def archive(self, index, *, legacy=False):
        name = f"QC_PHASE4_RESULT_20261004_1200{index:02d}_000001.zip"
        path = self.root / ("" if legacy else "results") / name
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("metadata.json", '{"version":"test"}')
            z.writestr("summary.json", '{"result":"TECHNICAL_PASS"}')
        os.utime(path, ns=(index * 1_000_000_000, index * 1_000_000_000))
        return path

    def duplicate(self, index):
        folder = self.root / "diagnostics/phase4" / f"20261004_1200{index:02d}_000001"
        folder.mkdir(parents=True)
        with zipfile.ZipFile(self.archives[index - 1]) as z:
            for name in z.namelist():
                (folder / name).write_bytes(z.read(name))
        return folder

    def test_preview_protects_five_latest_pointer_and_pinned_checkpoint(self):
        before = set((self.root / "results").iterdir())
        (self.root / "LAST_QC_RESULT.txt").write_text(f"FILE:\nC:\\old\\{self.archives[0].name}\n")
        (self.root / "results/pinned.json").write_text(json.dumps([self.archives[1].name]))
        plan = plan_cleanup(self.root)
        self.assertEqual([Path(c["path"]).name for c in plan["candidates"]], [self.archives[3].name, self.archives[2].name])
        self.assertTrue(before <= set((self.root / "results").iterdir()))
        result = apply_cleanup(self.root, plan)
        self.assertEqual(len(result["deleted"]), 2)
        self.assertTrue(self.archives[0].exists())
        self.assertTrue(self.archives[1].exists())
        self.assertTrue(all(p.exists() for p in self.archives[-5:]))

    def test_changed_candidate_invalidates_entire_plan_before_any_delete(self):
        plan = plan_cleanup(self.root)
        self.archives[0].write_bytes(b"changed")
        with self.assertRaises(ValueError):
            apply_cleanup(self.root, plan)
        self.assertTrue(all(p.exists() for p in self.archives))

    def test_new_pointer_or_pin_prevents_applying_an_old_plan(self):
        for protect in ("LAST_ALPHA_RESULT.txt", "results/pinned.json"):
            with self.subTest(protect=protect):
                plan = plan_cleanup(self.root)
                path = self.root / protect
                path.write_text(json.dumps([self.archives[0].name]) if protect.endswith("json") else self.archives[0].name)
                with self.assertRaises(ValueError):
                    apply_cleanup(self.root, plan)
                self.assertTrue(all(p.exists() for p in self.archives))
                path.unlink()

    def test_cleanup_is_blocked_while_a_capture_session_owns_runtime_lock(self):
        plan = plan_cleanup(self.root)
        lock = RuntimeLock(self.root / "runtime/overlay.lock")
        lock.acquire()
        try:
            with self.assertRaises(RuntimeError):
                apply_cleanup(self.root, plan)
        finally:
            lock.close()
        self.assertTrue(all(p.exists() for p in self.archives))

    def test_only_complete_verified_duplicate_diagnostics_are_removed(self):
        exact = self.duplicate(1)
        unique = self.duplicate(2)
        (unique / "unique-proof.png").write_bytes(b"only copy")
        plan = plan_cleanup(self.root)
        self.assertEqual(sum(c["diagnostics"] is not None for c in plan["candidates"]), 1)
        apply_cleanup(self.root, plan)
        self.assertFalse(exact.exists())
        self.assertTrue((unique / "unique-proof.png").exists())

    def test_changed_diagnostics_invalidates_plan_and_preserves_archive(self):
        folder = self.duplicate(1)
        plan = plan_cleanup(self.root)
        (folder / "summary.json").write_text("new content")
        with self.assertRaises(ValueError):
            apply_cleanup(self.root, plan)
        self.assertTrue(all(p.exists() for p in self.archives))

    def test_symlinks_and_corrupt_archives_are_preserved(self):
        external = self.root / "external.zip"
        external.write_bytes(b"unique")
        link = self.root / "results/QC_PHASE3_RESULT_external.zip"
        link.symlink_to(external)
        self.archives[0].write_bytes(b"corrupt")
        os.utime(self.archives[0], ns=(1_000_000_000, 1_000_000_000))
        plan = plan_cleanup(self.root)
        self.assertEqual(len(plan["skipped"]), 1)
        apply_cleanup(self.root, plan)
        self.assertTrue(self.archives[0].exists())
        self.assertEqual(external.read_bytes(), b"unique")
        self.assertTrue(link.is_symlink())

    def test_arbitrary_paths_and_duplicate_candidate_entries_are_rejected(self):
        for change in (lambda p: p["candidates"][0].update(path="../external.zip"),
                       lambda p: p["candidates"].append(copy.deepcopy(p["candidates"][0]))):
            plan = plan_cleanup(self.root)
            change(plan)
            with self.assertRaises(ValueError):
                apply_cleanup(self.root, plan)
            self.assertTrue(all(p.exists() for p in self.archives))

    def test_legacy_root_archives_are_eligible_but_retention_cannot_be_lowered(self):
        path = self.archive(0, legacy=True)
        self.assertIn(path.name, {c["path"] for c in plan_cleanup(self.root)["candidates"]})
        with self.assertRaises(ValueError):
            plan_cleanup(self.root, keep=4)

    def test_pinning_is_idempotent_and_blocks_a_pending_cleanup_plan(self):
        plan = plan_cleanup(self.root)
        pin_result(self.root, self.archives[0].name)
        pin_result(self.root, self.archives[0].name)
        names = json.loads((self.root / "results/pinned.json").read_text())
        self.assertEqual(names.count(self.archives[0].name), 1)
        with self.assertRaises(ValueError):
            apply_cleanup(self.root, plan)
        with self.assertRaises(ValueError):
            pin_result(self.root, "../unrelated.zip")


if __name__ == "__main__":
    unittest.main()
