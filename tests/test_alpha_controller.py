import json
from pathlib import Path
from queue import Queue
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from zipfile import ZipFile

from app.alpha_controller import AlphaController, _send
from app.runtime_lock import RuntimeLock


class LocalQueue(Queue):
    def close(self):
        pass


class AlphaControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.queue = LocalQueue(maxsize=32)
        self.alive = True
        self.now = 0.0
        self.process = Mock()
        self.process.is_alive.side_effect = lambda: self.alive
        self.process.terminate.side_effect = lambda: setattr(self, "alive", False)
        self.process.exitcode = 1
        self.context = SimpleNamespace(Queue=Mock(return_value=self.queue), Event=Mock(return_value=Mock()),
                                       Process=Mock(return_value=self.process))
        self.controller = AlphaController(self.root, context=self.context, clock=lambda: self.now)

    def test_duplicate_start_is_rejected_and_stop_is_idempotent(self):
        self.assertTrue(self.controller.start("alpha"))
        self.assertFalse(self.controller.start("qc_alpha"))
        self.context.Process.assert_called_once()
        self.controller.stop()
        self.now = 1.0
        self.controller.stop()
        self.assertEqual(self.controller.stop_at, 0.0)
        self.controller.stop_event.set.assert_called_once()

    def test_result_is_processed_before_worker_resources_close(self):
        self.controller.start("qc_alpha")
        self.queue.put({"type": "finished", "archive": "result.zip", "summary": {"result": "TECHNICAL_PASS"}})
        self.assertEqual(self.controller.poll()[0]["type"], "finished")
        self.assertTrue(self.controller.busy)
        self.alive = False
        self.controller.poll()
        self.assertFalse(self.controller.busy)
        self.process.close.assert_called_once()
        self.assertTrue(self.controller.start("alpha"))

    def test_worker_crash_without_result_gets_error_archive(self):
        self.controller.start("alpha")
        self.alive = False
        self.assertEqual(self.controller.poll(), [])
        self.now = 0.6
        update = self.controller.poll()[0]
        self.assertEqual(update["type"], "failed")
        self.assertFalse(self.controller.busy)
        with ZipFile(update["archive"]) as z:
            self.assertEqual(json.loads(z.read("summary.json"))["result"], "ERROR")

    def test_unresponsive_worker_is_terminated_and_partial_logs_are_packaged(self):
        self.controller.start("qc_alpha")
        session = self.root / "diagnostics" / "test"
        session.mkdir(parents=True)
        (session / "metadata.json").write_text("{}")
        (session / "events.jsonl").write_text('{"event":1}\n')
        self.queue.put({"type": "status", "session": str(session), "state": "running"})
        self.controller.poll()
        self.controller.stop()
        self.now = 13.0
        update = self.controller.poll()[0]
        self.process.terminate.assert_called_once()
        with ZipFile(update["archive"]) as z:
            self.assertIn("events.jsonl", z.namelist())
            self.assertEqual(json.loads(z.read("summary.json"))["stop_reason"], "worker_failure")

    def test_full_status_queue_does_not_block_runtime(self):
        q = Queue(maxsize=1)
        q.put({"old": True})
        _send(q, {"new": True})
        self.assertEqual(q.get_nowait(), {"old": True})


class RuntimeLockTests(unittest.TestCase):
    def test_lock_conflict_and_release_allow_the_next_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime/overlay.lock"
            first, second = RuntimeLock(path), RuntimeLock(path)
            first.acquire()
            try:
                with self.assertRaises(RuntimeError):
                    second.acquire()
            finally:
                first.close()
            second.acquire()
            second.close()


class SpawnedWorkerTests(unittest.TestCase):
    @unittest.skipIf(__import__('sys').platform == "win32", "Linux-only native failure smoke test")
    def test_real_spawn_returns_diagnostics_instead_of_leaving_panel_busy(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = AlphaController(Path(tmp))
            controller.start("qc_alpha")
            updates = []
            deadline = time.monotonic() + 5.0
            while controller.busy and time.monotonic() < deadline:
                updates.extend(controller.poll())
                time.sleep(0.02)
            if controller.busy:
                controller.stop()
                controller.process.terminate()
                controller.process.join(timeout=1)
                self.fail("Spawned worker failed to return within five seconds")
            result = next(r for r in updates if r["type"] == "failed")
            self.assertTrue(Path(result["archive"]).exists())
            self.assertIn("Windows-only", result["message"])
