from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def translated(self, dx: float, dy: float) -> "Rect":
        return Rect(self.x + dx, self.y + dy, self.w, self.h)

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


@dataclass
class OcrWord:
    text: str
    box: Rect

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "bbox": self.box.to_dict()}


@dataclass
class OcrLine:
    text: str
    box: Rect | None
    words: list[OcrWord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.box.to_dict() if self.box else None,
            "words": [word.to_dict() for word in self.words],
        }


@dataclass
class OcrResult:
    text: str
    lines: list[OcrLine]
    elapsed_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "lines": [line.to_dict() for line in self.lines],
        }


@dataclass
class DialogueContext:
    detected: bool
    layout: str
    confidence: float
    speaker: str | None
    text: str
    dialogue_box: Rect | None
    source_line_indexes: list[int] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected": self.detected,
            "layout": self.layout,
            "confidence": round(self.confidence, 3),
            "speaker": self.speaker,
            "text": self.text,
            "dialogue_box": self.dialogue_box.to_dict() if self.dialogue_box else None,
            "source_line_indexes": self.source_line_indexes,
            "reasons": self.reasons,
        }
