from __future__ import annotations

import re
from statistics import median

from .models import DialogueContext, OcrLine, Rect


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_UI_NOISE = {
    "continue",
    "close",
    "inventory",
    "options",
    "microtransactions",
    "social",
    "character",
}


def _clean(text: str) -> str:
    return " ".join(text.strip().split())


def _looks_like_sentence(text: str) -> bool:
    words = _WORD_RE.findall(text)
    if len(words) < 3:
        return False
    alpha = sum(ch.isalpha() for ch in text)
    return alpha >= max(8, int(len(text) * 0.5))


def _union(boxes: list[Rect]) -> Rect | None:
    if not boxes:
        return None
    left = min(b.x for b in boxes)
    top = min(b.y for b in boxes)
    right = max(b.right for b in boxes)
    bottom = max(b.bottom for b in boxes)
    return Rect(left, top, right - left, bottom - top)


class DialogueContextDetector:
    """Finds the likely story-dialogue cluster inside an OCR result.

    Coordinates are local to the capture ROI. The detector deliberately avoids
    hard-coding one exact rectangle: Spike 001 showed the panel shifts
    horizontally when inventory is open.
    """

    def __init__(self, capture_width: int, capture_height: int) -> None:
        self.capture_width = capture_width
        self.capture_height = capture_height

    def detect(self, lines: list[OcrLine]) -> DialogueContext:
        indexed: list[tuple[int, OcrLine]] = []
        for i, line in enumerate(lines):
            text = _clean(line.text)
            if not text or line.box is None:
                continue

            # Dialogue sits in the upper/middle part of our dedicated ROI.
            if line.box.cy > self.capture_height * 0.82:
                continue

            lower = text.casefold()
            if lower in _UI_NOISE:
                continue

            indexed.append((i, line))

        sentence_lines = [
            (i, line)
            for i, line in indexed
            if _looks_like_sentence(line.text) and len(line.text.strip()) >= 14
        ]

        if not sentence_lines:
            return DialogueContext(
                detected=False,
                layout="unknown",
                confidence=0.0,
                speaker=None,
                text="",
                dialogue_box=None,
                reasons=["no_sentence_like_ocr_lines"],
            )

        # Prefer vertically adjacent sentence lines. Story dialogue usually wraps
        # into 1–4 lines with similar x starts.
        groups: list[list[tuple[int, OcrLine]]] = []
        for item in sorted(sentence_lines, key=lambda x: (x[1].box.y, x[1].box.x)):
            if not groups:
                groups.append([item])
                continue

            prev = groups[-1][-1][1]
            cur = item[1]
            vertical_gap = cur.box.y - prev.box.bottom
            x_delta = abs(cur.box.x - prev.box.x)

            if vertical_gap <= self.capture_height * 0.10 and x_delta <= self.capture_width * 0.18:
                groups[-1].append(item)
            else:
                groups.append([item])

        def score_group(group: list[tuple[int, OcrLine]]) -> float:
            chars = sum(len(_clean(line.text)) for _, line in group)
            boxes = [line.box for _, line in group if line.box]
            starts = [b.x for b in boxes]
            x_spread = (max(starts) - min(starts)) if starts else self.capture_width
            coherence = max(0.0, 1.0 - x_spread / max(1.0, self.capture_width * 0.22))
            line_bonus = min(1.0, len(group) / 2.0)
            length_bonus = min(1.0, chars / 90.0)
            return 0.45 * length_bonus + 0.35 * coherence + 0.20 * line_bonus

        best = max(groups, key=score_group)
        score = score_group(best)

        best_boxes = [line.box for _, line in best if line.box]
        text = " ".join(_clean(line.text) for _, line in best)
        dialogue_box = _union(best_boxes)

        center_x = median([box.cx for box in best_boxes]) if best_boxes else self.capture_width / 2
        layout = "inventory_left" if center_x < self.capture_width * 0.48 else "normal_right"

        # Speaker is usually a short line immediately above the dialogue block.
        speaker = None
        if dialogue_box is not None:
            speaker_candidates: list[tuple[float, str]] = []
            for _, line in indexed:
                if line.box is None:
                    continue
                text_candidate = _clean(line.text)
                if not text_candidate or _looks_like_sentence(text_candidate):
                    continue
                if len(_WORD_RE.findall(text_candidate)) > 5:
                    continue
                gap = dialogue_box.y - line.box.bottom
                if -3 <= gap <= self.capture_height * 0.13:
                    if abs(line.box.cx - dialogue_box.cx) <= self.capture_width * 0.25:
                        speaker_candidates.append((abs(gap), text_candidate))
            if speaker_candidates:
                speaker = min(speaker_candidates, key=lambda x: x[0])[1]

        confidence = min(0.99, score)
        reasons = [
            f"sentence_lines={len(sentence_lines)}",
            f"group_lines={len(best)}",
            f"layout={layout}",
        ]
        if speaker:
            confidence = min(0.99, confidence + 0.08)
            reasons.append("speaker_candidate_found")

        return DialogueContext(
            detected=confidence >= 0.45,
            layout=layout,
            confidence=confidence,
            speaker=speaker,
            text=text,
            dialogue_box=dialogue_box,
            source_line_indexes=[i for i, _ in best],
            reasons=reasons,
        )
