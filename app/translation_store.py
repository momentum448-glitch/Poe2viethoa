from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .text_normalize import token_key
from .translation_models import TranslationRecord


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS translations (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    normalized_source TEXT NOT NULL,
    vi TEXT NOT NULL,
    speaker TEXT,
    area TEXT,
    content_type TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_translations_normalized
    ON translations(normalized_source);
CREATE INDEX IF NOT EXISTS idx_translations_context
    ON translations(content_type, speaker, area, status);

CREATE TABLE IF NOT EXISTS aliases (
    translation_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    FOREIGN KEY(translation_id) REFERENCES translations(id)
);
CREATE INDEX IF NOT EXISTS idx_aliases_normalized
    ON aliases(normalized_alias);
"""


def load_json_records(path: Path) -> list[TranslationRecord]:
    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array")

    records: list[TranslationRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid translation record in {path}")

        records.append(
            TranslationRecord(
                id=str(item["id"]),
                source=str(item["source"]),
                vi=str(item["vi"]),
                speaker=item.get("speaker"),
                area=item.get("area"),
                content_type=str(item.get("type", "dialogue")),
                status=str(item.get("status", "draft")),
                aliases=tuple(str(x) for x in item.get("aliases", [])),
            )
        )
    return records


def build_sqlite(records: Iterable[TranslationRecord], db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)

        for record in records:
            normalized = token_key(record.source)
            if not normalized:
                raise ValueError(f"Record {record.id} has an empty normalized source")

            conn.execute(
                """
                INSERT INTO translations
                    (id, source, normalized_source, vi, speaker, area, content_type, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.source,
                    normalized,
                    record.vi,
                    record.speaker,
                    record.area,
                    record.content_type,
                    record.status,
                ),
            )

            for alias in record.aliases:
                normalized_alias = token_key(alias)
                if normalized_alias:
                    conn.execute(
                        """
                        INSERT INTO aliases
                            (translation_id, alias, normalized_alias)
                        VALUES (?, ?, ?)
                        """,
                        (record.id, alias, normalized_alias),
                    )

        conn.commit()
    finally:
        conn.close()


class TranslationStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    def all_records(
        self,
        *,
        content_type: str = "dialogue",
        statuses: tuple[str, ...] = ("reviewed", "approved"),
    ) -> list[TranslationRecord]:
        placeholders = ",".join("?" for _ in statuses)
        rows = self._conn.execute(
            f"""
            SELECT * FROM translations
            WHERE content_type = ?
              AND status IN ({placeholders})
            """,
            (content_type, *statuses),
        ).fetchall()

        return [self._record_from_row(row) for row in rows]

    def exact(
        self,
        normalized_text: str,
        *,
        speaker: str | None = None,
        area: str | None = None,
        content_type: str = "dialogue",
        statuses: tuple[str, ...] = ("reviewed", "approved"),
    ) -> TranslationRecord | None:
        placeholders = ",".join("?" for _ in statuses)
        params: list[object] = [normalized_text, content_type, *statuses]

        query = f"""
            SELECT t.*, 0 AS via_alias
            FROM translations t
            WHERE t.normalized_source = ?
              AND t.content_type = ?
              AND t.status IN ({placeholders})
        """

        if speaker:
            query += " AND (t.speaker IS NULL OR lower(t.speaker) = lower(?))"
            params.append(speaker)
        if area:
            query += " AND (t.area IS NULL OR lower(t.area) = lower(?))"
            params.append(area)

        query += " ORDER BY CASE t.status WHEN 'approved' THEN 0 ELSE 1 END LIMIT 1"
        row = self._conn.execute(query, params).fetchone()
        if row:
            return self._record_from_row(row)

        alias_params: list[object] = [normalized_text, content_type, *statuses]
        alias_query = f"""
            SELECT t.*, 1 AS via_alias
            FROM aliases a
            JOIN translations t ON t.id = a.translation_id
            WHERE a.normalized_alias = ?
              AND t.content_type = ?
              AND t.status IN ({placeholders})
        """
        if speaker:
            alias_query += " AND (t.speaker IS NULL OR lower(t.speaker) = lower(?))"
            alias_params.append(speaker)
        if area:
            alias_query += " AND (t.area IS NULL OR lower(t.area) = lower(?))"
            alias_params.append(area)
        alias_query += " ORDER BY CASE t.status WHEN 'approved' THEN 0 ELSE 1 END LIMIT 1"

        row = self._conn.execute(alias_query, alias_params).fetchone()
        return self._record_from_row(row) if row else None

    def aliases_for(self, record_id: str) -> tuple[str, ...]:
        rows = self._conn.execute(
            "SELECT alias FROM aliases WHERE translation_id = ?",
            (record_id,),
        ).fetchall()
        return tuple(row["alias"] for row in rows)

    def _record_from_row(self, row: sqlite3.Row) -> TranslationRecord:
        return TranslationRecord(
            id=row["id"],
            source=row["source"],
            vi=row["vi"],
            speaker=row["speaker"],
            area=row["area"],
            content_type=row["content_type"],
            status=row["status"],
            aliases=self.aliases_for(row["id"]),
        )
