"""Offline translation batches: source-bound drafts, QA, review and publication."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid
import zipfile

from app.text_normalize import token_key
from app.translation_store import load_source_corpus, load_vi_entries

ROOT = Path(__file__).resolve().parents[1]
STATES = {"draft", "reviewed", "approved"}
PLACEHOLDERS = re.compile(r"\{[^{}\n]+\}|%(?:\d+\$)?[sdif]")
NUMBERS = re.compile(r"\d+(?:[.,]\d+)?")


def digest(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def inputs(root: Path) -> tuple[dict, dict, list[dict]]:
    corpus = load_source_corpus(root / "source_data/dialogue_corpus.jsonl")
    if not corpus:
        raise ValueError("Thiếu nguồn local. Chạy SOURCE_SYNC.bat trước.")
    lock = json.loads((root / "sources/sources.lock.json").read_text(encoding="utf-8"))
    source_ref = lock["sources"]["poe2_en"]["ref"]
    context_ref = lock["sources"]["dialogue_context"]["ref"]
    for row in corpus.values():
        if row.get("source_snapshot") != source_ref:
            raise ValueError("Corpus khác nguồn đã pin; đồng bộ lại trước khi soạn lô.")
        if row.get("context_snapshot") not in (None, context_ref):
            raise ValueError("Context khác nguồn đã pin; đồng bộ lại trước khi soạn lô.")
    glossary = json.loads((root / "translations/glossary.json").read_text(encoding="utf-8"))
    if glossary.get("schema") != 1 or not isinstance(glossary.get("terms"), list):
        raise ValueError("Glossary không đúng schema 1.")
    catalog = load_vi_entries(root / "translations/dialogue_vi.json")
    catalog_index(catalog)
    return corpus, glossary, catalog


def catalog_index(entries: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for entry in entries:
        sid = entry.get("source_id")
        if not isinstance(sid, str) or not sid or sid in indexed:
            raise ValueError(f"source_id thiếu/trùng trong catalog: {sid}")
        if entry.get("status", "draft") not in STATES:
            raise ValueError(f"Trạng thái catalog không hợp lệ: {sid}")
        indexed[sid] = entry
    return indexed


def pins(root: Path) -> dict[str, str]:
    return {key: hashlib.sha256((root / path).read_bytes()).hexdigest()
            for key, path in {"source_lock_sha256": "sources/sources.lock.json",
                              "glossary_sha256": "translations/glossary.json"}.items()}


def select_qc(root: Path, archive: Path) -> tuple[list[str], list[str]]:
    """Only exact fresh-source MISS text is eligible; never turn fuzzy chat into data."""
    corpus, _, catalog = inputs(root)
    known = {e["source_id"] for e in catalog if e.get("status") in {"reviewed", "approved"}}
    by_text: dict[str, list[str]] = defaultdict(list)
    for sid, row in corpus.items():
        by_text[token_key(row["source"])].append(sid)
    with zipfile.ZipFile(archive) as z:
        info = z.getinfo("events.jsonl")
        if info.file_size > 16 * 1024 * 1024:
            raise ValueError("Event log quá lớn cho một lô QC.")
        events = z.read(info).decode("utf-8-sig").splitlines()
    selected: list[str] = []
    unresolved: list[str] = []
    for raw in events:
        event = json.loads(raw)
        dialogue = event.get("dialogue", {})
        pipeline = event.get("pipeline", {})
        match = pipeline.get("translation") or {}
        if not (dialogue.get("detected") and pipeline.get("emit")
                and match.get("matched") is False):
            continue
        choices = by_text.get(token_key(dialogue.get("text", "")), [])
        speaker = dialogue.get("speaker")
        if speaker:
            choices = [sid for sid in choices if corpus[sid].get("speaker") in (None, speaker)]
        # Shared normalized text with different IDs/contexts must be chosen manually.
        if len(choices) != 1:
            unresolved.append(str(event.get("event", "unknown")))
        elif choices[0] not in known and choices[0] not in selected:
            selected.append(choices[0])
    return selected, unresolved


def prepare(root: Path, source_ids: list[str], batch_id: str, output: Path) -> dict:
    if output.exists():
        raise ValueError("Lô đã tồn tại; không ghi đè công việc đang duyệt.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", batch_id):
        raise ValueError("batch_id chỉ dùng chữ, số, dấu chấm/gạch.")
    corpus, _, catalog = inputs(root)
    current = catalog_index(catalog)
    ids = list(dict.fromkeys(source_ids))
    if not ids:
        raise ValueError("Không có câu mới đủ điều kiện.")
    entries = []
    for sid in ids:
        if sid not in corpus:
            raise ValueError(f"Không có source_id trong nguồn mới: {sid}")
        row = corpus[sid]
        entries.append({"source_id": sid, "source_sha256": text_sha(row["source"]),
                        "speaker": row.get("speaker"), "topic": row.get("topic"),
                        "segment_index": row.get("segment_index"),
                        "segment_count": row.get("segment_count"),
                        "base_translation_sha256": digest(current[sid]) if sid in current else None,
                        "vi": "", "status": "draft"})
    batch = {"schema": 1, "batch_id": batch_id, "language": "vi",
             "created_at": timestamp(), **pins(root), "entries": entries}
    atomic_json(output, batch)
    return batch


def review_digest(batch: dict, entry: dict) -> str:
    return digest({**{k: batch.get(k) for k in ("batch_id", "source_lock_sha256", "glossary_sha256")},
                   **{k: entry.get(k) for k in ("source_id", "source_sha256", "vi", "speaker", "topic",
                                               "segment_index", "segment_count")}})


def contains(text: str, phrase: str, *, case_sensitive: bool = False) -> bool:
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, flags) is not None


def qa(root: Path, batch: dict) -> dict:
    if not isinstance(batch, dict):
        raise ValueError("Lô cần một JSON object, không phải array.")
    corpus, glossary, _ = inputs(root)
    issues: list[dict] = []

    def issue(sid: str, code: str, message: str, severity: str = "error") -> None:
        issues.append({"source_id": sid, "code": code, "severity": severity, "message": message})

    if batch.get("schema") != 1 or batch.get("language") != "vi":
        issue("batch", "schema", "Lô cần schema 1 và language=vi.")
    for key, value in pins(root).items():
        if batch.get(key) != value:
            issue("batch", "stale_" + key, "Nguồn/glossary đã đổi; tạo và duyệt lại lô.")
    entries = batch.get("entries")
    if not isinstance(entries, list) or not entries:
        issue("batch", "empty_batch", "Lô thiếu entries.")
        entries = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            issue("batch", "invalid_entry", "Entry không phải object.")
            continue
        sid = entry.get("source_id")
        if not isinstance(sid, str) or sid not in corpus:
            issue(str(sid), "missing_source", "Câu không tồn tại trong nguồn local.")
            continue
        if sid in seen:
            issue(sid, "duplicate_source", "Một source_id xuất hiện nhiều lần.")
        seen.add(sid)
        row = corpus[sid]
        source = row["source"]
        if entry.get("source_sha256") != text_sha(source):
            issue(sid, "changed_source", "Nội dung nguồn khác lúc tạo nháp.")
        for key in ("speaker", "topic", "segment_index", "segment_count"):
            if row.get(key) != entry.get(key):
                issue(sid, "changed_context", "Speaker/topic khác lúc tạo nháp.")
        vi = entry.get("vi")
        if not isinstance(vi, str) or not vi.strip():
            issue(sid, "empty_translation", "Chưa có bản dịch tiếng Việt.")
            continue
        if vi != vi.strip() or "\n" in vi or "\r" in vi:
            issue(sid, "whitespace", "Bản dịch phải là một đoạn, không có khoảng trắng thừa.")
        if vi.casefold() == source.casefold() and len(source.split()) >= 3:
            issue(sid, "untranslated_copy", "Bản dịch còn nguyên câu tiếng Anh.")
        if re.search(r"<[^>]+>", vi) or any(ord(c) < 32 for c in vi):
            issue(sid, "control_markup", "Bản dịch chứa markup/ký tự điều khiển.")
        if Counter(PLACEHOLDERS.findall(source)) != Counter(PLACEHOLDERS.findall(vi)):
            issue(sid, "placeholders", "Thiếu/đổi placeholder của nguồn.")
        if Counter(NUMBERS.findall(source)) != Counter(NUMBERS.findall(vi)):
            issue(sid, "numbers", "Thiếu/đổi chữ số của nguồn.")
        for term in glossary["terms"]:
            if contains(source, term["source"], case_sensitive=term.get("case_sensitive", False)):
                if not contains(vi, term["target"]):
                    issue(sid, "glossary", f"Thiếu thuật ngữ: {term['target']}")
        if len(vi) > max(400, len(source) * 2.2):
            issue(sid, "long_translation", "Bản dịch dài bất thường; kiểm tra nghĩa và độ vừa overlay.", "warning")
        status = entry.get("status")
        if status not in STATES:
            issue(sid, "invalid_status", "Trạng thái chỉ được draft/reviewed/approved.")
        elif status in {"reviewed", "approved"}:
            if not entry.get("reviewer") or not entry.get("review_note"):
                issue(sid, "missing_review", "Thiếu người duyệt/ghi chú soát nghĩa.")
            if entry.get("review_sha256") != review_digest(batch, entry):
                issue(sid, "edited_after_review", "Bản dịch/dấu nguồn đã đổi sau khi duyệt.")
            if status == "approved" and (not entry.get("approved_by")
                    or entry.get("approval_sha256") != review_digest(batch, entry)):
                issue(sid, "missing_approval", "Approved cần dấu QC của người dùng.")
    errors = sum(i["severity"] == "error" for i in issues)
    return {"batch_id": batch.get("batch_id"), "entries": len(entries),
            "errors": errors, "warnings": len(issues) - errors, "passed": errors == 0,
            "issues": issues}


def mark_reviewed(root: Path, batch: dict, reviewer: str, note: str) -> dict:
    if not reviewer.strip() or not note.strip():
        raise ValueError("Cần người duyệt và ghi chú soát nghĩa.")
    # Work on a copy so a failed review cannot mutate the caller's draft.
    candidate = json.loads(json.dumps(batch))
    for entry in candidate["entries"]:
        if entry.get("status") not in STATES:
            raise ValueError("Trạng thái lô không hợp lệ.")
        if entry.get("status") == "approved":
            raise ValueError("Không hạ trạng thái approved; tạo lô sửa đổi mới.")
        entry.update(status="draft")
    report = qa(root, candidate)
    if not report["passed"]:
        raise ValueError(json.dumps(report, ensure_ascii=False))
    for entry in candidate["entries"]:
        entry.update(status="reviewed", reviewer=reviewer.strip(), review_note=note.strip(),
                     reviewed_at=timestamp())
        entry["review_sha256"] = review_digest(candidate, entry)
    return candidate


def approve(root: Path, batch: dict, human_reviewer: str, note: str) -> dict:
    if not human_reviewer.strip() or not note.strip():
        raise ValueError("Cần tên người QC và ghi chú xác nhận.")
    if not qa(root, batch)["passed"] or any(e.get("status") != "reviewed" for e in batch["entries"]):
        raise ValueError("Chỉ approved lô đã reviewed và QA đạt.")
    candidate = json.loads(json.dumps(batch))
    for entry in candidate["entries"]:
        entry.update(status="approved", approved_by=human_reviewer.strip(),
                     approval_note=note.strip(), approved_at=timestamp())
        entry["approval_sha256"] = review_digest(candidate, entry)
    return candidate


def publish(root: Path, batch: dict) -> dict:
    report = qa(root, batch)
    if not report["passed"]:
        raise ValueError(json.dumps(report, ensure_ascii=False))
    if any(e["status"] == "draft" for e in batch["entries"]):
        raise ValueError("Bản nháp chưa được đưa vào runtime; soát nghĩa và mark-reviewed trước.")
    path = root / "translations/dialogue_vi.json"
    old = load_vi_entries(path)
    current = catalog_index(old)
    changed = 0
    for entry in batch["entries"]:
        sid = entry["source_id"]
        existing = current.get(sid)
        same_content = existing and all(existing.get(k) == entry.get(k)
                                        for k in ("vi", "source_sha256"))
        rank = {"draft": 0, "reviewed": 1, "approved": 2}
        if same_content and rank[existing.get("status", "draft")] >= rank[entry["status"]]:
            continue
        # A published reviewed batch can be promoted after real human QC, without
        # pretending its original pre-publication base is still the active catalog.
        promotion = (same_content and existing.get("factory_batch") == batch["batch_id"]
                     and existing.get("review") == entry.get("reviewer")
                     and existing.get("status") == "reviewed" and entry["status"] == "approved")
        if not promotion and (digest(existing) if existing else None) != entry.get("base_translation_sha256"):
            raise ValueError(f"Catalog đã đổi khi đang duyệt: {sid}. Tạo lô từ dữ liệu mới.")
        if existing and existing.get("status") == "approved" and entry["status"] != "approved":
            raise ValueError(f"Không thay bản approved bằng reviewed: {sid}")
        current[sid] = {**(existing or {}), "source_id": sid, "vi": entry["vi"],
                        "status": entry["status"], "review": entry["reviewer"],
                        "source_sha256": entry["source_sha256"], "vi_sha256": text_sha(entry["vi"]),
                        "factory_batch": batch["batch_id"], "review_note": entry["review_note"]}
        if entry["status"] == "approved":
            current[sid].update(approved_by=entry["approved_by"], approval_note=entry["approval_note"])
        changed += 1
    merged = list(current.values())
    if changed:
        atomic_json(path, merged)
    return {"changed": changed, "translation_entries": len(merged),
            "displayable_entries": sum(e.get("status") in {"reviewed", "approved"} for e in merged)}


def render_bundle(root: Path, batch: dict) -> str:
    """Local English/VI review packet with same-topic pages and reviewed TM references."""
    corpus, glossary, catalog = inputs(root)
    lines = [f"# Translation batch: {batch['batch_id']}", "",
             "Translate/review each complete page. Return only source_id and vi edits in the batch JSON.",
             "Do not change source hashes, context, or review state. Automatic QA is not semantic review.", "",
             "## Project style", *[f"- {s}" for s in glossary.get("style", [])], ""]
    for entry in batch["entries"]:
        row = corpus[entry["source_id"]]
        lines += [f"## {entry['source_id']} — {row.get('speaker')} / {row.get('topic')}", "",
                  f"English: {row['source']}", "", f"Vietnamese: {entry['vi'] or '(draft needed)'}", ""]
        neighbors = [r for r in corpus.values() if row.get("topic") and row.get("speaker")
                     and r.get("speaker") == row["speaker"] and r.get("topic") == row["topic"]
                     and r.get("upstream_index") == row.get("upstream_index")
                     and r.get("source_table") == row.get("source_table")
                     and r["source_id"] != row["source_id"]]
        for neighbor in sorted(neighbors, key=lambda r: r.get("segment_index", 0))[:8]:
            lines += [f"Adjacent page ({neighbor.get('segment_index')}): {neighbor['source']}"]
        references = []
        source_tokens = set(token_key(row["source"]).split())
        for memory in catalog:
            previous = corpus.get(memory["source_id"])
            if not previous or memory.get("status") not in {"reviewed", "approved"}:
                continue
            if previous.get("speaker") != row.get("speaker"):
                continue
            tokens = set(token_key(previous["source"]).split())
            score = len(tokens & source_tokens) / max(1, len(tokens | source_tokens))
            references.append((score, memory, previous))
        for _, memory, previous in sorted(references, key=lambda x: x[0], reverse=True)[:2]:
            lines += ["", f"Reviewed memory ({memory['source_id']}): {previous['source']}",
                      f"VI: {memory['vi']}"]
        lines += [""]
    lines += ["## Automated QA", "", "```json", json.dumps(qa(root, batch), ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("prepare")
    create.add_argument("--batch-id", required=True)
    create.add_argument("--source-id", action="append", default=[])
    create.add_argument("--from-qc", type=Path)
    create.add_argument("--output", type=Path, required=True)
    for name in ("qa", "bundle", "mark-reviewed", "approve", "publish"):
        command = commands.add_parser(name)
        command.add_argument("--batch", type=Path, required=True)
        if name == "bundle":
            command.add_argument("--output", type=Path, required=True)
        if name in {"mark-reviewed", "approve"}:
            command.add_argument("--reviewer", required=True)
            command.add_argument("--note", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            source_ids = args.source_id
            if args.from_qc:
                selected, unresolved = select_qc(args.root, args.from_qc)
                source_ids += selected
                if unresolved:
                    print("Unresolved QC events (not selected): " + ", ".join(unresolved))
            batch = prepare(args.root, source_ids, args.batch_id, args.output)
            print(f"Created {args.output}: {len(batch['entries'])} drafts")
            return
        batch = json.loads(args.batch.read_text(encoding="utf-8"))
        if args.command == "qa":
            report = qa(args.root, batch)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            raise SystemExit(0 if report["passed"] else 1)
        if args.command == "bundle":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render_bundle(args.root, batch), encoding="utf-8")
            print(args.output)
        elif args.command == "mark-reviewed":
            atomic_json(args.batch, mark_reviewed(args.root, batch, args.reviewer, args.note))
            print("Marked reviewed after explicit semantic review; not human-approved.")
        elif args.command == "approve":
            atomic_json(args.batch, approve(args.root, batch, args.reviewer, args.note))
            print("Marked approved with the supplied human-QC record.")
        else:
            print(json.dumps(publish(args.root, batch), ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"[ERROR] {exc}\n")


if __name__ == "__main__":
    main()
