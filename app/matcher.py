from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from rapidfuzz import fuzz

from .text_normalize import token_key, tokenize
from .translation_models import (
    MatchCandidate,
    TranslationRecord,
    TranslationResult,
)
from .translation_store import TranslationStore


@dataclass(frozen=True)
class MatcherConfig:
    high_threshold: float = 90.0
    medium_threshold: float = 78.0
    ambiguity_margin: float = 4.0
    max_candidates: int = 80
    debug_candidates: int = 5


class DialogueMatcher:
    """Exact-first matcher with an inverted token index for fuzzy fallback."""

    def __init__(
        self,
        store: TranslationStore,
        *,
        config: MatcherConfig | None = None,
    ) -> None:
        self.store = store
        self.config = config or MatcherConfig()
        self.records = store.all_records(content_type="dialogue")
        self._records_by_id = {record.id: record for record in self.records}

        self._token_index: dict[str, set[str]] = defaultdict(set)
        self._normalized_by_id: dict[str, tuple[str, ...]] = {}

        for record in self.records:
            variants = [token_key(record.source)]
            variants.extend(token_key(alias) for alias in record.aliases)
            variants = [v for v in variants if v]
            self._normalized_by_id[record.id] = tuple(variants)

            for variant in variants:
                for token in set(tokenize(variant)):
                    if len(token) >= 2:
                        self._token_index[token].add(record.id)

    def match(
        self,
        text: str,
        *,
        speaker: str | None = None,
        area: str | None = None,
    ) -> TranslationResult:
        normalized = token_key(text)

        if not normalized:
            return TranslationResult(
                matched=False,
                confidence="low",
                score=0.0,
                method="empty",
                source_ocr=text,
                normalized_ocr=normalized,
                record=None,
            )

        exact = self.store.exact(
            normalized,
            speaker=speaker,
            area=area,
            content_type="dialogue",
        )
        if exact:
            return TranslationResult(
                matched=True,
                confidence="high",
                score=100.0,
                method="exact",
                source_ocr=text,
                normalized_ocr=normalized,
                record=exact,
            )

        candidate_ids = self._candidate_ids(normalized, speaker=speaker, area=area)
        scored: list[MatchCandidate] = []

        for record_id in candidate_ids:
            record = self._records_by_id[record_id]
            best = 0.0
            for variant in self._normalized_by_id.get(record_id, ()):
                # token_set_ratio tolerates OCR word-order/noise while ratio
                # preserves sentence-shape sensitivity.
                token_score = float(fuzz.token_set_ratio(normalized, variant))
                ratio_score = float(fuzz.ratio(normalized, variant))
                score = 0.65 * token_score + 0.35 * ratio_score
                best = max(best, score)

            if best > 0:
                scored.append(MatchCandidate(record, best, "fuzzy"))

        scored.sort(key=lambda c: c.score, reverse=True)
        scored = scored[: self.config.debug_candidates]

        if not scored:
            return TranslationResult(
                matched=False,
                confidence="low",
                score=0.0,
                method="no_candidate",
                source_ocr=text,
                normalized_ocr=normalized,
                record=None,
            )

        best = scored[0]
        runner_up = scored[1] if len(scored) > 1 else None
        ambiguous = (
            runner_up is not None
            and best.score - runner_up.score < self.config.ambiguity_margin
        )

        # Normal mode only displays high-confidence results. A fuzzy result
        # that is almost tied with another candidate is intentionally
        # downgraded to medium so the overlay hides it instead of guessing.
        if best.score >= self.config.high_threshold and not ambiguous:
            confidence = "high"
            matched = True
        elif best.score >= self.config.medium_threshold:
            confidence = "medium"
            matched = True
        else:
            confidence = "low"
            matched = False

        return TranslationResult(
            matched=matched,
            confidence=confidence,
            score=round(best.score, 2),
            method="fuzzy",
            source_ocr=text,
            normalized_ocr=normalized,
            record=best.record if matched else None,
            candidates=tuple(scored),
        )

    def _candidate_ids(
        self,
        normalized: str,
        *,
        speaker: str | None,
        area: str | None,
    ) -> list[str]:
        counts: dict[str, int] = defaultdict(int)
        for token in set(tokenize(normalized)):
            for record_id in self._token_index.get(token, ()):
                record = self._records_by_id[record_id]
                if speaker and record.speaker and record.speaker.casefold() != speaker.casefold():
                    continue
                if area and record.area and record.area.casefold() != area.casefold():
                    continue
                counts[record_id] += 1

        ranked = sorted(counts, key=lambda rid: counts[rid], reverse=True)
        return ranked[: self.config.max_candidates]
