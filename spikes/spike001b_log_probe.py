from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ZONE_RE = re.compile(r'Generating level\s+\d+\s+area\s+"([^"]+)"', re.I)

def ps_process_paths() -> list[Path]:
    cmd = [
        "powershell", "-NoProfile", "-Command",
        "$p=Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'PathOfExile|Path of Exile' }; "
        "$p | ForEach-Object { $_.ExecutablePath }"
    ]
    try:
        out = subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace", timeout=12)
    except Exception:
        return []
    result = []
    for line in out.splitlines():
        line = line.strip()
        if line:
            p = Path(line)
            if p.exists():
                result.append(p)
    return result

def candidates() -> tuple[list[Path], list[str]]:
    found_processes = ps_process_paths()
    c: list[Path] = []
    for exe in found_processes:
        d = exe.parent
        c += [
            d / "logs" / "Client.txt",
            d / "logs" / "KakaoClient.txt",
            d.parent / "logs" / "Client.txt",
        ]

    user = Path(os.environ.get("USERPROFILE", str(Path.home())))
    c += [
        user / "Documents" / "My Games" / "Path of Exile 2" / "logs" / "Client.txt",
        user / "Documents" / "My Games" / "Path of Exile 2" / "Logs" / "Client.txt",
    ]

    for drive in ("C:", "D:", "E:", "F:", "G:"):
        b = Path(drive + os.sep)
        c += [
            b / "Program Files (x86)" / "Steam" / "steamapps" / "common" / "Path of Exile 2" / "logs" / "Client.txt",
            b / "Program Files" / "Steam" / "steamapps" / "common" / "Path of Exile 2" / "logs" / "Client.txt",
            b / "SteamLibrary" / "steamapps" / "common" / "Path of Exile 2" / "logs" / "Client.txt",
            b / "Program Files (x86)" / "Grinding Gear Games" / "Path of Exile 2" / "logs" / "Client.txt",
            b / "Program Files" / "Grinding Gear Games" / "Path of Exile 2" / "logs" / "Client.txt",
            b / "Program Files (x86)" / "Grinding Gear Games" / "logs" / "Client.txt",
            b / "Program Files" / "Grinding Gear Games" / "logs" / "Client.txt",
        ]

    seen = set()
    uniq = []
    for p in c:
        k = str(p).casefold()
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq, [str(p) for p in found_processes]

def tail_bytes(path: Path, max_bytes: int = 8 * 1024 * 1024) -> str:
    with path.open("rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - max_bytes))
        data = f.read()
    return data.decode("utf-8", errors="replace")

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = root / "diagnostics" / "spike001b" / stamp
    out.mkdir(parents=True, exist_ok=True)

    cands, procs = candidates()
    existing = [p for p in cands if p.is_file()]
    existing.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    selected = existing[0] if existing else None

    report = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "process_executable_paths": procs,
        "selected_log": str(selected) if selected else None,
        "existing_candidates": [str(p) for p in existing],
        "checked_candidates": [str(p) for p in cands],
    }

    if not selected:
        (out / "log_probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[FAIL] Client.txt not found.")
        print("Evidence:", out)
        return 2

    tail = tail_bytes(selected)
    (out / "client_tail.log").write_text(tail, encoding="utf-8")

    renly = [line for line in tail.splitlines() if "Renly" in line]
    dialogueish = []
    for line in tail.splitlines():
        low = line.casefold()
        if any(k in low for k in ("renly", "phaaryl", "bloody flowers", "riverbank", "branoc")):
            dialogueish.append(line)

    zones = []
    for line in tail.splitlines():
        m = ZONE_RE.search(line)
        if m:
            zones.append({"area_id": m.group(1), "line": line})

    (out / "renly_hits.txt").write_text("\n".join(dialogueish), encoding="utf-8")
    (out / "zone_hits.json").write_text(json.dumps(zones[-100:], ensure_ascii=False, indent=2), encoding="utf-8")

    report.update({
        "tail_bytes_read": len(tail.encode("utf-8", errors="replace")),
        "renly_literal_line_count": len(renly),
        "dialogue_keyword_hit_count": len(dialogueish),
        "zone_event_count_in_tail": len(zones),
    })
    (out / "log_probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[OK] Client.txt:", selected)
    print("[OK] Renly literal lines:", len(renly))
    print("[OK] Dialogue keyword hits:", len(dialogueish))
    print("[OK] Zone events in tail:", len(zones))
    print("Evidence:", out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
