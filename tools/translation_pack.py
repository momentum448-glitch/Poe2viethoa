"""Source-verified complete-topic selection, resumable batches and coverage."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

from tools.source_sync import CONTINUE_RE, parse_dictionary_table, source_id
from tools.translation_factory import atomic_json, digest, inputs, pins, prepare, qa, text_sha


def validate_manifest(root: Path, manifest: dict) -> dict:
    corpus, _, catalog = inputs(root)
    if manifest.get("schema") != 1 or not re.fullmatch(r"[A-Za-z0-9_.-]{1,70}", manifest.get("manifest_id", "")):
        raise ValueError("Manifest không đúng schema/id.")
    if manifest.get("source_lock_sha256") != pins(root)["source_lock_sha256"]:
        raise ValueError("Manifest khác nguồn đã pin.")
    entries = manifest.get("entries", [])
    if not entries:
        raise ValueError("Manifest trống.")
    declared = {}
    for entry in entries:
        sid = entry["source_id"]
        if sid in declared or sid not in corpus or entry.get("source_sha256") != text_sha(corpus[sid]["source"]):
            raise ValueError(f"Source thiếu/trùng/đã đổi: {sid}")
        declared[sid] = entry
    lock = json.loads((root / "sources/sources.lock.json").read_text(encoding="utf-8"))
    raw = {}
    upstream = lock["sources"]["poe2_en"]
    for remote in upstream["files"]:
        table = Path(remote).stem
        path = root / "source_data/cache" / f"{upstream['ref']}-{Path(remote).name}"
        if not path.is_file():
            raise ValueError("Thiếu snapshot cache; chạy dev/SOURCE_SYNC.bat.")
        for row in parse_dictionary_table(path, table):
            raw[(table, row["upstream_index"])] = row
    referenced = set()
    seen = set()
    for group in manifest.get("groups", []):
        key = (group["source_table"], group["upstream_index"])
        row = raw.get(key)
        if key in seen or not row or group.get("source_sha256") != text_sha(row["full_text"]):
            raise ValueError(f"Nhóm nguồn thiếu/trùng/đã đổi: {key}")
        seen.add(key)
        expected = [source_id(key[0], part.strip()) for part in CONTINUE_RE.split(row["full_text"]) if part.strip()]
        if group.get("page_ids") != expected:
            raise ValueError(f"Topic thiếu/đảo trang Continue: {key}")
        # Identical pages can belong to several variants. Verify one canonical
        # context anchor, while retaining every original page reference.
        anchors = [corpus[sid] for sid in expected if sid in corpus]
        if not any(r.get("speaker") == group["speaker"] and r.get("topic") == group["topic"]
                   and r.get("upstream_index") == key[1] for r in anchors):
            raise ValueError(f"Nhóm thiếu context anchor: {key}")
        if any(sid not in declared for sid in expected):
            raise ValueError(f"Nhóm thiếu source ID trong manifest: {key}")
        referenced.update(expected)
    if referenced != set(declared):
        raise ValueError("Manifest có trang không thuộc nhóm đã kiểm tra.")
    baseline = manifest.get("baseline_ids", [])
    if not isinstance(baseline, list) or len(set(baseline)) != len(baseline) or not set(baseline) <= referenced:
        raise ValueError("Danh sách baseline không hợp lệ.")
    return {"corpus": corpus, "catalog": {e["source_id"]: e for e in catalog}, "ids": list(declared)}


def prepare_pack(root: Path, manifest: dict, output: Path, *, size: int = 40,
                 speakers: list[str] | None = None, topics: list[str] | None = None) -> dict:
    validate_manifest(root, manifest)
    if not 1 <= size <= 100:
        raise ValueError("Cỡ lô phải từ 1 đến 100 trang.")
    baseline = set(manifest.get("baseline_ids", []))
    assigned = set(baseline)
    chunks = []
    current = []
    npc = None
    for group in manifest["groups"]:
        if speakers and group["speaker"] not in speakers:
            continue
        if topics and group["topic"] not in topics:
            continue
        fresh = list(dict.fromkeys(sid for sid in group["page_ids"] if sid not in assigned))
        if not fresh:
            continue
        if len(fresh) > size:
            raise ValueError("Một topic lớn hơn cỡ lô; tăng --size để không cắt nhóm.")
        if current and (npc != group["speaker"] or len(current) + len(fresh) > size):
            chunks.append((npc, current))
            current = []
        npc = group["speaker"]
        current.extend(fresh)
        assigned.update(fresh)
    if current:
        chunks.append((npc, current))
    if (speakers or topics) and not chunks:
        raise ValueError("Bộ lọc không có trang mới trong manifest.")
    matches = [p for p in (root / "translations/manifests").glob("*.json")
               if json.loads(p.read_text(encoding="utf-8")) == manifest]
    if len(matches) != 1:
        raise ValueError("Manifest cần được lưu duy nhất trong translations/manifests/.")
    manifest_path = matches[0]
    suffix = "-" + digest(sorted(set(topics)))[:8] if topics else ""
    paths = []
    counters = Counter()
    # Layout is based on immutable manifest baseline, so publishing earlier
    # batches cannot reshuffle names or overwrite unfinished work on resume.
    for speaker, ids in chunks:
        counters[speaker] += 1
        slug = re.sub(r"[^a-z0-9]+", "-", speaker.casefold()).strip("-")
        bid = f"{manifest['manifest_id']}{suffix}-{slug}-{counters[speaker]:02d}"
        path = output / f"{bid}.json"
        if path.exists():
            batch = json.loads(path.read_text(encoding="utf-8"))
            if batch.get("batch_id") != bid or [e["source_id"] for e in batch["entries"]] != ids:
                raise ValueError(f"Lô đã tồn tại khác selection: {path}")
            report = qa(root, batch)
            if any(i["code"] not in {"empty_translation"} for i in report["issues"]):
                raise ValueError(f"Lô cần sửa/duyệt lại trước khi resume: {path}")
            state = "resumed"
        else:
            batch = prepare(root, ids, bid, path)
            batch.update(manifest_path=manifest_path.relative_to(root).as_posix(),
                         manifest_sha256=text_sha(manifest_path.read_text(encoding="utf-8")))
            atomic_json(path, batch)
            state = "created"
        paths.append({"path": str(path), "speaker": speaker, "pages": len(ids), "state": state})
    return {"manifest": manifest["manifest_id"], "batches": paths,
            "selected_pages": sum(p["pages"] for p in paths), "baseline_pages": len(baseline)}


def coverage(root: Path, manifest: dict) -> dict:
    checked = validate_manifest(root, manifest)
    catalog = checked["catalog"]
    by_npc = {}
    missing = []
    for sid in checked["ids"]:
        row = checked["corpus"][sid]
        npc = row.get("speaker") or "Unknown"
        counts = by_npc.setdefault(npc, {"total": 0, "reviewed": 0, "approved": 0, "missing": 0})
        counts["total"] += 1
        status = catalog.get(sid, {}).get("status")
        if status in {"reviewed", "approved"}:
            counts[status] += 1
        else:
            counts["missing"] += 1
            missing.append(sid)
    complete = sum(all(catalog.get(s, {}).get("status") in {"reviewed", "approved"}
                       for s in g["page_ids"]) for g in manifest["groups"])
    return {"manifest": manifest["manifest_id"], "total": len(checked["ids"]),
            "displayable": len(checked["ids"]) - len(missing), "missing_ids": missing,
            "complete_groups": complete, "groups": len(manifest["groups"]), "by_npc": by_npc}
