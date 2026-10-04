from __future__ import annotations

import hashlib
from pathlib import Path

VERSION = "0.5.0-alpha.2"
BUILD_ID = "act1-20261004-01"


def build_info(root: Path) -> dict[str, str]:
    """Identify the actual source bundle, including downloads without a .git folder."""
    paths = list((root / "app").glob("*.py")) + list((root / "tools").glob("*.py"))
    paths += [root / "requirements.txt", root / "sources/sources.lock.json",
              root / "translations/dialogue_vi.json", root / "translations/glossary.json"]
    paths += list((root / "translations/batches").glob("*.json"))
    paths += list((root / "translations/manifests").glob("*.json"))
    digest = hashlib.sha256()
    for path in sorted(paths):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return {"version": VERSION, "build_id": BUILD_ID, "code_sha256": digest.hexdigest()}
