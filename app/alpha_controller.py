"""Spawn the Windows overlay on its own main thread; keep the control panel responsive."""
from __future__ import annotations

import asyncio
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
import json
import multiprocessing
from pathlib import Path
from queue import Empty, Full
import time
from typing import Any

STOP_TIMEOUT_SECONDS = 12.0


def _send(messages, payload: dict[str, Any], *, final: bool = False) -> None:
    try:
        if final:
            messages.put(payload, timeout=1.0)
        else:
            messages.put_nowait(payload)
    except (Full, OSError, ValueError):
        pass


def recover_session(root: Path, session: Path | None, message: str, *, mode: str) -> Path:
    """Package a worker crash/forced stop honestly, including any existing evidence."""
    from .session_runtime import append_jsonl, package_session, write_json
    from .version import build_info

    if session is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        session = root / "diagnostics" / "recovery" / stamp
        session.mkdir(parents=True, exist_ok=False)
        write_json(session / "metadata.json", {"mode": mode, **build_info(root)})
    old_summary = session / "summary.json"
    try:
        summary = json.loads(old_summary.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        summary = {"mode": mode, **build_info(root)}
    summary.update({"result": "ERROR", "stop_reason": "worker_failure",
                    "message": message, "finished_at": datetime.now().isoformat(timespec="seconds"),
                    "visual_qc_required": mode != "alpha"})
    append_jsonl(session / "errors.jsonl", {"stage": "worker", "fatal": True, "message": message},
                 max_bytes=1024 * 1024)
    write_json(old_summary, summary)
    return package_session(root, session, mode=mode)


def session_worker(root_text: str, mode: str, stop_event, messages) -> None:
    root = Path(root_text)
    session = None

    def status(payload):
        nonlocal session
        session = Path(payload["session"])
        _send(messages, {"type": "status", **payload})

    try:
        from .session_runtime import run
        # pythonw has no console. Discard routine console output; structured
        # errors/events are persisted by the session runner instead.
        import os
        with open(os.devnull, "w", encoding="utf-8") as sink, redirect_stdout(sink), redirect_stderr(sink):
            session, archive = asyncio.run(run(
                None if mode == "alpha" else 60, 0.12, root / "runtime/translations.sqlite3",
                mode=mode, should_stop=stop_event.is_set, on_status=status, output_root=root,
            ))
        summary = json.loads((session / "summary.json").read_text(encoding="utf-8"))
        _send(messages, {"type": "finished", "archive": str(archive), "summary": summary,
                         "session": str(session)}, final=True)
    except BaseException as exc:
        message = f"{type(exc).__name__}: {exc}"
        try:
            archive = recover_session(root, session, message, mode=mode)
            archive_text = str(archive)
        except Exception as packing_error:
            archive_text = ""
            message += f"; chưa tạo được ZIP: {packing_error}"
        _send(messages, {"type": "failed", "archive": archive_text, "message": message}, final=True)


class AlphaController:
    def __init__(self, root: Path, *, context=None, clock=time.monotonic) -> None:
        self.root = root
        self.context = context or multiprocessing.get_context("spawn")
        self.clock = clock
        self.process = None
        self.messages = None
        self.stop_event = None
        self.stop_at: float | None = None
        self.finished_received = False
        self.exited_at: float | None = None
        self.session: Path | None = None
        self.mode = "alpha"

    @property
    def busy(self) -> bool:
        return self.process is not None

    def start(self, mode: str) -> bool:
        if self.busy:
            return False
        if mode not in {"alpha", "qc_alpha"}:
            raise ValueError("Unknown Alpha mode")
        self.mode = mode
        self.messages = self.context.Queue(maxsize=32)
        self.stop_event = self.context.Event()
        self.process = self.context.Process(
            target=session_worker, args=(str(self.root), mode, self.stop_event, self.messages),
            name="POE2-overlay", daemon=True,
        )
        self.stop_at = None
        self.exited_at = None
        self.finished_received = False
        self.session = None
        try:
            self.process.start()
        except BaseException:
            self.process = None
            self._close_queue()
            raise
        return True

    def stop(self) -> None:
        if self.busy and self.stop_at is None:
            self.stop_at = self.clock()
            self.stop_event.set()

    def _close_queue(self) -> None:
        if self.messages is not None:
            self.messages.close()
            self.messages = None

    def _recovery(self, reason: str) -> dict[str, Any]:
        try:
            archive = recover_session(self.root, self.session, reason, mode=self.mode)
            return {"type": "failed", "message": reason, "archive": str(archive)}
        except Exception as exc:
            return {"type": "failed", "message": f"{reason}; chưa tạo được ZIP: {exc}", "archive": ""}

    def poll(self) -> list[dict[str, Any]]:
        if not self.busy:
            return []
        updates: list[dict[str, Any]] = []
        for _ in range(64):
            try:
                message = self.messages.get_nowait()
            except Empty:
                break
            updates.append(message)
            if message.get("session"):
                self.session = Path(message["session"])
            if message["type"] in {"finished", "failed"}:
                self.finished_received = True

        now = self.clock()
        if self.stop_at is not None and now - self.stop_at >= STOP_TIMEOUT_SECONDS and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=0.2)
            if not self.process.is_alive():
                if not self.finished_received:
                    updates.append(self._recovery("Phiên không phản hồi khi dừng; đã đóng overlay và ghi chẩn đoán lỗi."))
                    self.finished_received = True
        if not self.process.is_alive():
            # The queue feeder can deliver the last result just after process exit.
            if self.exited_at is None:
                self.exited_at = now
            if self.finished_received or now - self.exited_at >= 0.5:
                if not self.finished_received:
                    updates.append(self._recovery(f"Tiến trình overlay dừng bất thường (mã {self.process.exitcode})."))
                self.process.join(timeout=0)
                self.process.close()
                self.process = None
                self._close_queue()
        return updates
