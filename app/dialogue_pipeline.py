from __future__ import annotations

from dataclasses import dataclass

from .matcher import DialogueMatcher
from .text_stabilizer import TextStabilizer
from .translation_models import TranslationResult


@dataclass(frozen=True)
class PipelineDecision:
    emit: bool
    reason: str
    translation: TranslationResult | None


class DialogueTranslationPipeline:
    """Text-level dedupe followed by translation matching."""

    def __init__(
        self,
        matcher: DialogueMatcher,
        *,
        stabilizer: TextStabilizer | None = None,
    ) -> None:
        self.matcher = matcher
        self.stabilizer = stabilizer or TextStabilizer(duplicate_similarity=0.94)

    def process(
        self,
        text: str,
        *,
        speaker: str | None = None,
        area: str | None = None,
        layout: str | None = None,
    ) -> PipelineDecision:
        stable = self.stabilizer.observe(
            text,
            speaker=speaker,
            layout=layout,
        )

        if not stable.emit:
            return PipelineDecision(False, stable.reason, None)

        result = self.matcher.match(
            text,
            speaker=speaker,
            area=area,
        )
        return PipelineDecision(True, stable.reason, result)
