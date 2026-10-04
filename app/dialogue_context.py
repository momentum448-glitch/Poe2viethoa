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
    "goodbye",
}


def _clean(text: str) -> str:
    return " ".join(text.strip().split())


def _looks_like_sentence(text: str) -> bool:
    words = _WORD_RE.findall(text)
    if len(words) < 3:
        return False
    alpha = sum(ch.isalpha() for ch in text)
    return alpha >= max(8, int(len(text) * 0.5))


def _looks_like_continuation(text: str) -> bool:
    text = _clean(text)
    if not text:
        return False
    if text.casefold() in _UI_NOISE:
        return False
    alpha = sum(ch.isalpha() for ch in text)
    if alpha < 4:
        return False
    # Short wrapped dialogue lines often look like "truth." or
    # "war in stone.". UI menu labels usually do not end in sentence punctuation.
    return text[-1:] in ".!?…" or text[:1].islower()


def _union(boxes: list[Rect]) -> Rect | None:
    if not boxes:
        return None
    left = min(b.x for b in boxes)
    top = min(b.y for b in boxes)
    right = max(b.right for b in boxes)
    bottom = max(b.bottom for b in boxes)
    return Rect(left, top, right - left, bottom - top)


class DialogueContextDetector:
    """Find the likely story-dialogue cluster inside an OCR result.

    Spike 001 established two horizontal layouts at 1920×1080: normal dialogue
    and the left-shifted inventory-open layout. This detector uses relative
    geometry so the same logic can scale with the capture ROI.
    """

    def __init__(self, capture_width: int, capture_height: int) -> None:
        self.capture_width = capture_width
        self.capture_height = capture_height

    def detect(self, lines: list[OcrLine]) -> DialogueContext:
        indexed: list[tuple[int, OcrLine]] = []
        continue_present = False

        for i, line in enumerate(lines):
            text = _clean(line.text)
            if not text or line.box is None:
                continue

            lower = text.casefold()
            if lower == "continue":
                # Strong story-dialogue cue observed in the real Spike 001 frames.
                if line.box.cy < self.capture_height * 0.90:
                    continue_present = True
                continue

            # Bottom of the ROI can contain global chat. Keep it out before any
            # sentence scoring happens.
            if line.box.cy > self.capture_height * 0.82:
                continue

            if lower in _UI_NOISE:
                continue

            indexed.append((i, line))

        seed_lines = [
            (i, line)
            for i, line in indexed
            if _looks_like_sentence(line.text) and len(line.text.strip()) >= 14
        ]

        if not seed_lines:
            return DialogueContext(
                detected=False,
                layout="unknown",
                confidence=0.0,
                speaker=None,
                text="",
                dialogue_box=None,
                reasons=["no_sentence_like_ocr_lines"],
            )

        # Group long sentence-like lines first.
        groups: list[list[tuple[int, OcrLine]]] = []
        for item in sorted(seed_lines, key=lambda x: (x[1].box.y, x[1].box.x)):
            if not groups:
                groups.append([item])
                continue

            prev = groups[-1][-1][1]
            cur = item[1]
            vertical_gap = cur.box.y - prev.box.bottom
            x_delta = abs(cur.box.x - prev.box.x)

            if (
                vertical_gap <= self.capture_height * 0.10
                and x_delta <= self.capture_width * 0.18
            ):
                groups[-1].append(item)
            else:
                groups.append([item])

        # Add short wrapped tail lines that sentence heuristics would otherwise
        # drop ("truth.", "became.", "war in stone."). Require a tight left-edge
        # alignment so NPC menu labels are not glued onto a dialogue paragraph.
        all_by_y = sorted(indexed, key=lambda x: (x[1].box.y, x[1].box.x))
        for group in groups:
            changed = True
            while changed:
                changed = False
                last_i, last_line = group[-1]
                for candidate_i, candidate in all_by_y:
                    if candidate_i in {i for i, _ in group}:
                        continue
                    if candidate.box.y < last_line.box.y:
                        continue

                    vertical_gap = candidate.box.y - last_line.box.bottom
                    x_delta = abs(candidate.box.x - last_line.box.x)
                    if vertical_gap > self.capture_height * 0.10:
                        break

                    if (
                        x_delta <= max(36.0, self.capture_width * 0.04)
                        and _looks_like_continuation(candidate.text)
                    ):
                        group.append((candidate_i, candidate))
                        changed = True
                        break

        def score_group(group: list[tuple[int, OcrLine]]) -> float:
            chars = sum(len(_clean(line.text)) for _, line in group)
            boxes = [line.box for _, line in group if line.box]
            starts = [b.x for b in boxes]
            x_spread = (max(starts) - min(starts)) if starts else self.capture_width
            coherence = max(
                0.0,
                1.0 - x_spread / max(1.0, self.capture_width * 0.22),
            )
            line_bonus = min(1.0, len(group) / 2.0)
            length_bonus = min(1.0, chars / 90.0)
            return 0.45 * length_bonus + 0.35 * coherence + 0.20 * line_bonus

        best = max(groups, key=score_group)
        score = score_group(best)

        best_boxes = [line.box for _, line in best if line.box]
        text = " ".join(_clean(line.text) for _, line in best)
        dialogue_box = _union(best_boxes)

        center_x = (
            median([box.cx for box in best_boxes])
            if best_boxes
            else self.capture_width / 2
        )
        layout = (
            "inventory_left"
            if center_x < self.capture_width * 0.48
            else "normal_right"
        )

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

                # Real Spike 001 speaker labels sit in the upper third of the ROI.
                # This excludes topic/menu labels such as "The Devourer".
                if line.box.cy > self.capture_height * 0.33:
                    continue

                gap = dialogue_box.y - line.box.bottom
                if -3 <= gap <= self.capture_height * 0.15:
                    if abs(line.box.cx - dialogue_box.cx) <= self.capture_width * 0.25:
                        speaker_candidates.append((abs(gap), text_candidate))

            if speaker_candidates:
                speaker = min(speaker_candidates, key=lambda x: x[0])[1]

        confidence = min(0.99, score)
        reasons = [
            f"seed_lines={len(seed_lines)}",
            f"group_lines={len(best)}",
            f"layout={layout}",
        ]

        if speaker:
            confidence = min(0.99, confidence + 0.08)
            reasons.append("speaker_candidate_found")

        if continue_present:
            confidence = min(0.99, confidence + 0.08)
            reasons.append("continue_cue_found")

        # At least one dialogue-specific anchor is required. This rejects the
        # ESC menu and other sentence-shaped UI while still tolerating one OCR
        # miss (speaker OR Continue).
        anchored = bool(speaker or continue_present)
        detected = anchored and confidence >= 0.62

        if not anchored:
            reasons.append("no_dialogue_anchor")

        return DialogueContext(
            detected=detected,
            layout=layout,
            confidence=confidence,
            speaker=speaker,
            text=text if detected else "",
            dialogue_box=dialogue_box if detected else None,
            source_line_indexes=[i for i, _ in best] if detected else [],
            reasons=reasons,
        )
