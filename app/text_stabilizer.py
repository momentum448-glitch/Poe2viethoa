from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import time

from .text_normalize import token_key


@dataclass(frozen=True)
class StableTextDecision:
    emit: bool
    normalized: str
    similarity_to_previous: float
    reason: str


class TextStabilizer:
    """Suppress repeated OCR of the same visible dialogue.

    The screen can animate continuously, causing OCR to run again even though
    the dialogue text has not changed. This layer protects matching/overlay
    work from those duplicate OCR results.
    """

    def __init__(
        self,
        *,
        duplicate_similarity: float = 0.965,
        repeat_after_seconds: float = 15.0,
    ) -> None:
        self.duplicate_similarity = duplicate_similarity
        self.repeat_after_seconds = repeat_after_seconds
        self._last_key: str | None = None
        self._last_speaker: str | None = None
        self._last_layout: str | None = None
        self._last_emitted_at: float | None = None

    def reset(self) -> None:
        self._last_key = None
        self._last_speaker = None
        self._last_layout = None
        self._last_emitted_at = None

    def observe(
        self,
        text: str,
        *,
        speaker: str | None = None,
        layout: str | None = None,
        now: float | None = None,
    ) -> StableTextDecision:
        now = time.monotonic() if now is None else now
        key = token_key(text)

        if not key:
            return StableTextDecision(False, "", 0.0, "empty")

        if self._last_key is None:
            self._remember(key, speaker, layout, now)
            return StableTextDecision(True, key, 0.0, "first_text")

        same_context = (
            (speaker or "").casefold() == (self._last_speaker or "").casefold()
            and (layout or "") == (self._last_layout or "")
        )
        similarity = SequenceMatcher(None, self._last_key, key).ratio()

        age = (
            now - self._last_emitted_at
            if self._last_emitted_at is not None
            else self.repeat_after_seconds + 1.0
        )

        if (
            same_context
            and similarity >= self.duplicate_similarity
            and age < self.repeat_after_seconds
        ):
            return StableTextDecision(False, key, similarity, "duplicate")

        self._remember(key, speaker, layout, now)
        reason = "context_changed" if not same_context else "text_changed"
        return StableTextDecision(True, key, similarity, reason)

    def _remember(
        self,
        key: str,
        speaker: str | None,
        layout: str | None,
        now: float,
    ) -> None:
        self._last_key = key
        self._last_speaker = speaker
        self._last_layout = layout
        self._last_emitted_at = now
