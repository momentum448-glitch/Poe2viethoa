from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


TranslationStatus = Literal["draft", "reviewed", "approved"]


@dataclass(frozen=True)
class TranslationRecord:
    id: str
    source: str
    vi: str
    speaker: str | None = None
    area: str | None = None
    content_type: str = "dialogue"
    status: TranslationStatus = "draft"
    aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MatchCandidate:
    record: TranslationRecord
    score: float
    method: str


@dataclass(frozen=True)
class TranslationResult:
    matched: bool
    confidence: str
    score: float
    method: str
    source_ocr: str
    normalized_ocr: str
    record: TranslationRecord | None
    candidates: tuple[MatchCandidate, ...] = field(default_factory=tuple)

    @property
    def should_display_normal(self) -> bool:
        return self.matched and self.confidence == "high" and self.record is not None
