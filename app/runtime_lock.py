from __future__ import annotations

import os
from pathlib import Path


class RuntimeLock:
    """One capture/overlay session per installation; OS releases locks on exit."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._file = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise RuntimeError("Một phiên overlay đang chạy. Hãy dừng phiên đó trước.") from exc
        self._file = stream

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
