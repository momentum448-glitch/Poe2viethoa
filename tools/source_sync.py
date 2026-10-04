from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "sources" / "sources.lock.json"
SOURCE_ROOT = ROOT / "source_data"
CACHE_DIR = SOURCE_ROOT / "cache"
VAULT_DIR = SOURCE_ROOT / "vault"
CORPUS_PATH = SOURCE_ROOT / "dialogue_corpus.jsonl"
REPORT_PATH = SOURCE_ROOT / "source_sync_report.json"

CONTINUE_RE = re.compile(r"\s*<continue>\s*", re.IGNORECASE)
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
AUDIO_RE = re.compile(r"^!\[\[")


def read_lock() -> dict[str, Any]:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def download(url: str, target: Path, *, force: bool = False) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0 and not force:
        return target

    tmp = target.with_suffix(target.suffix + ".part")
    if tmp.exists():
        tmp.unlink()

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "POE2Viethoa-source-sync/1.0"},
    )
    with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as f:
        shutil.copyfileobj(response, f)

    tmp.replace(target)
    return target


def normalize_compare(text: str) -> str:
    text = CONTINUE_RE.sub(" ", text)
    text = re.sub(r"[{}<>]", " ", text)
    text = text.replace("’", "'").replace("‘", "'")
    text = text.casefold()
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return " ".join(text.split())


def normalize_segment(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'")
    text = text.casefold()
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return " ".join(text.split())


def fingerprint(text: str) -> str:
    normalized = normalize_segment(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def source_id(table: str, text: str) -> str:
    return f"dlg_{table.lower()}_{fingerprint(text)[:20]}"


def english_values(entry: dict[str, Any]) -> Iterable[str]:
    for value in entry.get("columns", {}).get("Text", []):
        if not isinstance(value, dict):
            continue
        text = str(value.get("en") or "").strip()
        if text:
            yield text


def parse_dictionary_table(path: Path, table_name: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []

    for entry in payload.get("entries", []):
        for text in english_values(entry):
            rows.append(
                {
                    "table": table_name,
                    "upstream_index": entry.get("index"),
                    "upstream_id": entry.get("id"),
                    "full_text": text,
                    "compare_key": normalize_compare(text),
                }
            )
    return rows


def parse_vault_markdown(path: Path) -> list[dict[str, str]]:
    speaker = path.stem
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    records: list[dict[str, str]] = []
    topic: str | None = None
    prose: list[str] = []

    def flush() -> None:
        nonlocal prose
        text = " ".join(x.strip() for x in prose if x.strip()).strip()
        prose = []
        if topic and text:
            records.append(
                {
                    "speaker": speaker,
                    "topic": topic,
                    "text": text,
                    "compare_key": normalize_compare(text),
                    "vault_path": str(path),
                }
            )

    for line in lines:
        heading = HEADING_RE.match(line)
        if heading:
            flush()
            topic = heading.group(1).strip()
            continue

        if AUDIO_RE.match(line):
            flush()
            continue

        if topic and line.strip():
            prose.append(line)

    flush()
    return records


def ensure_vault(lock: dict[str, Any], *, force: bool) -> Path:
    source = lock["sources"]["dialogue_context"]
    archive = CACHE_DIR / f"exiled-vault-{source['ref']}.zip"
    download(source["archive"], archive, force=force)

    marker = VAULT_DIR / ".ref"
    if (
        not force
        and VAULT_DIR.exists()
        and marker.exists()
        and marker.read_text(encoding="utf-8").strip() == source["ref"]
    ):
        return VAULT_DIR

    if VAULT_DIR.exists():
        shutil.rmtree(VAULT_DIR)
    VAULT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            normalized = info.filename.replace("\\", "/")
            needle = "/Exiled Vault Dialogue/PoE2/"
            if needle not in normalized or not normalized.lower().endswith(".md"):
                continue

            relative = normalized.split(needle, 1)[1]
            target = VAULT_DIR / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    marker.write_text(source["ref"] + "\n", encoding="utf-8")
    return VAULT_DIR


def build_context_index(vault_dir: Path) -> tuple[dict[str, list[dict[str, str]]], int]:
    index: dict[str, list[dict[str, str]]] = defaultdict(list)
    total = 0
    for path in vault_dir.rglob("*.md"):
        for record in parse_vault_markdown(path):
            key = record["compare_key"]
            if key:
                index[key].append(record)
                total += 1
    return index, total


def fetch_source_tables(lock: dict[str, Any], *, force: bool) -> list[dict[str, Any]]:
    source = lock["sources"]["poe2_en"]
    repo = source["repo"]
    ref = source["ref"]
    all_rows: list[dict[str, Any]] = []

    for remote_path in source["files"]:
        name = Path(remote_path).name
        target = CACHE_DIR / f"{ref}-{name}"
        url = f"https://raw.githubusercontent.com/{repo}/{ref}/{remote_path}"
        download(url, target, force=force)
        table = Path(remote_path).stem
        all_rows.extend(parse_dictionary_table(target, table))

    return all_rows


def build_corpus(
    source_rows: list[dict[str, Any]],
    context_index: dict[str, list[dict[str, str]]],
    *,
    source_ref: str,
    context_ref: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    corpus: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    context_exact = 0
    context_ambiguous = 0
    context_missing = 0

    for row in source_rows:
        contexts = context_index.get(row["compare_key"], [])
        context: dict[str, str] | None = None

        if len(contexts) == 1:
            context = contexts[0]
            context_exact += 1
        elif len(contexts) > 1:
            context_ambiguous += 1
        else:
            context_missing += 1

        segments = [
            part.strip()
            for part in CONTINUE_RE.split(row["full_text"])
            if part.strip()
        ]

        for segment_index, segment in enumerate(segments):
            sid = source_id(row["table"], segment)

            # Same displayed segment can legitimately appear in more than one
            # source row. Keep a single matcher record but preserve source refs.
            if sid in seen_source_ids:
                continue
            seen_source_ids.add(sid)

            record = {
                "source_id": sid,
                "source_fingerprint": fingerprint(segment),
                "source": segment,
                "source_table": row["table"],
                "source_snapshot": source_ref,
                "upstream_index": row["upstream_index"],
                "upstream_id": row["upstream_id"],
                "segment_index": segment_index,
                "segment_count": len(segments),
                "speaker": context["speaker"] if context else None,
                "topic": context["topic"] if context else None,
                "context_snapshot": context_ref if context else None,
                "context_path": context["vault_path"] if context else None,
                "context_method": "exact_transcript" if context else None,
            }
            corpus.append(record)

    stats = {
        "source_rows": len(source_rows),
        "corpus_segments": len(corpus),
        "context_exact_rows": context_exact,
        "context_ambiguous_rows": context_ambiguous,
        "context_missing_rows": context_missing,
        "with_speaker": sum(1 for r in corpus if r["speaker"]),
        "without_speaker": sum(1 for r in corpus if not r["speaker"]),
    }
    return corpus, stats


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    lock = read_lock()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/4] Downloading pinned English source tables...")
    source_rows = fetch_source_tables(lock, force=args.force)

    context_error = None
    context_index: dict[str, list[dict[str, str]]] = {}
    vault_records = 0

    print("[2/4] Downloading/extracting dialogue context snapshot (optional)...")
    try:
        vault_dir = ensure_vault(lock, force=args.force)
        print("[3/4] Building speaker/topic context index...")
        context_index, vault_records = build_context_index(vault_dir)
    except Exception as exc:
        context_error = f"{type(exc).__name__}: {exc}"
        print(f"[WARN] Context enrichment unavailable: {context_error}")
        print("[WARN] Continuing with English source only.")

    print("[4/4] Building local source corpus...")
    source_ref = lock["sources"]["poe2_en"]["ref"]
    context_ref = lock["sources"]["dialogue_context"]["ref"]
    corpus, stats = build_corpus(
        source_rows,
        context_index,
        source_ref=source_ref,
        context_ref=context_ref,
    )
    write_jsonl(CORPUS_PATH, corpus)

    report = {
        "status": "OK",
        "source_ref": source_ref,
        "context_ref": context_ref,
        "vault_transcript_records": vault_records,
        "context_error": context_error,
        **stats,
        "corpus_path": str(CORPUS_PATH.relative_to(ROOT)),
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("SOURCE SYNC COMPLETE")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
