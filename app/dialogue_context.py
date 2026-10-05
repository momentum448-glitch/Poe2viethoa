from __future__ import annotations

import re
from statistics import median

from .models import DialogueContext, OcrLine, Rect


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_UI_NOISE = {
    "continue", "close", "inventory", "options", "microtransactions", "social",
    "character", "goodbye", "buy or sell items", "disenchant", "gamble", "trade",
}
_DEFAULT_SPEAKERS = {"Una", "Renly", "Finn", "The Hooded One"}


def _clean(text: str) -> str:
    return " ".join(text.strip().split())


def _looks_like_sentence(text: str) -> bool:
    words = _WORD_RE.findall(text)
    alpha = sum(ch.isalpha() for ch in text)
    return len(words) >= 3 and alpha >= max(8, int(len(text) * 0.5))


def _looks_like_continuation(text: str) -> bool:
    text = _clean(text)
    return (bool(text) and text.casefold() not in _UI_NOISE
            and sum(ch.isalpha() for ch in text) >= 4
            and (text[-1:] in ".!?…" or text[:1].islower()))


def _union(boxes: list[Rect]) -> Rect | None:
    if not boxes:
        return None
    left, top = min(b.x for b in boxes), min(b.y for b in boxes)
    right, bottom = max(b.right for b in boxes), max(b.bottom for b in boxes)
    return Rect(left, top, right - left, bottom - top)


def _line_geometry(line: OcrLine) -> tuple[float, float, float]:
    # One over-tall word rectangle must not split a real paragraph. Keep the
    # union for the mask, but use the typical word baseline for line grouping.
    if len(line.words) >= 3:
        return (median(word.box.y for word in line.words),
                median(word.box.bottom for word in line.words),
                median(word.box.h for word in line.words))
    return line.box.y, line.box.bottom, line.box.h


def _spatial_lines(line: OcrLine) -> list[OcrLine]:
    """Windows OCR may join chat and a paragraph on the same baseline."""
    if not line.words:
        return [line]
    height = median(word.box.h for word in line.words)
    chunks = []
    current = []
    for word in sorted(line.words, key=lambda item: item.box.x):
        if current and (word.box.x - current[-1].box.right > max(30, height * 3)
                        or abs(word.box.cy - current[-1].box.cy) > height * 0.75):
            chunks.append(current)
            current = []
        current.append(word)
    chunks.append(current)
    if len(chunks) == 1:
        return [line]
    return [OcrLine(" ".join(word.text for word in chunk),
                    _union([word.box for word in chunk]), chunk) for chunk in chunks]


class DialogueContextDetector:
    """Associate a local paragraph, known NPC header and Continue at any position.

    Distances come from the OCR font height, not a screen band or the size of
    the capture. Unrelated columns remain separate even on a full game frame.
    """

    def __init__(self, capture_width: int, capture_height: int, *,
                 known_speakers: set[str] | None = None) -> None:
        self.capture_width = capture_width
        self.capture_height = capture_height
        self.speakers = {name.casefold(): name for name in
                         (_DEFAULT_SPEAKERS if known_speakers is None else known_speakers)}

    def detect(self, lines: list[OcrLine]) -> DialogueContext:
        indexed = []
        headers = []
        footers = []
        for i, raw_line in enumerate(lines):
            for line in _spatial_lines(raw_line):
                box, text = line.box, _clean(line.text)
                if (box is None or not text or box.w <= 0 or box.h <= 0
                        or box.x < 0 or box.y < 0
                        or box.right > self.capture_width or box.bottom > self.capture_height):
                    continue
                key = text.casefold().strip(" :.")
                if key == "continue":
                    footers.append(box)
                elif key in self.speakers:
                    headers.append((self.speakers[key], box))
                elif key not in _UI_NOISE:
                    indexed.append((i, line))

        seeds = {(i, id(line)) for i, line in indexed
                 if _looks_like_sentence(line.text) and len(line.text.strip()) >= 14}
        body_lines = [(i, line) for i, line in indexed
                      if (i, id(line)) in seeds or _looks_like_continuation(line.text)]
        groups = []
        for item in sorted(body_lines, key=lambda x: (_line_geometry(x[1])[0], x[1].box.x)):
            box = item[1].box
            line_top, _, line_height = _line_geometry(item[1])
            choices = []
            for group in groups:
                last_bottom = _line_geometry(group[-1][1])[1]
                font_height = median(_line_geometry(line)[2] for _, line in group)
                # A neighboring chat column used to pass the ROI-wide x margin.
                left_delta = abs(box.x - median(line.box.x for _, line in group))
                gap = line_top - last_bottom
                if (-min(font_height, line_height) * 0.25 <= gap <= font_height * 1.5
                        and left_delta <= max(12, min(font_height, line_height) * 0.9)
                        and 0.6 <= line_height / font_height <= 1.65):
                    choices.append((abs(gap) + left_delta, group))
            if choices:
                min(choices, key=lambda item: item[0])[1].append(item)
            else:
                groups.append([item])
        groups = [group for group in groups if any((i, id(line)) in seeds for i, line in group)]
        if not groups:
            return DialogueContext(False, "unknown", 0.0, None, "", None,
                                   reasons=["no_sentence_like_ocr_lines"])

        def anchors(group):
            paragraph = _union([line.box for _, line in group])
            font_height = median(_line_geometry(line)[2] for _, line in group)
            margin = max(12, font_height * 2)
            nearby_footers = [box for box in footers
                              if -3 <= box.y - paragraph.bottom <= font_height * 7
                              and paragraph.x - margin <= box.cx <= paragraph.right + margin]
            footer = min(nearby_footers, key=lambda box: box.y, default=None)
            nearby_headers = [(name, box) for name, box in headers
                              if -3 <= paragraph.y - box.bottom <= font_height * 3.5
                              and paragraph.x - margin <= box.cx <= paragraph.right + margin]
            header = min(nearby_headers, key=lambda item: paragraph.y - item[1].bottom,
                         default=(None, None))
            # A clipped paragraph at the capture edge must not win via its header.
            # There may be further lines/Continue outside the captured image.
            clipped = footer is None and paragraph.bottom > self.capture_height - font_height * 0.5
            # Topic menus can have a known header but no sentence punctuation.
            sentence_end = any(_clean(line.text)[-1:] in ".!?…" for _, line in group)
            anchored = not clipped and (footer is not None or (header[0] and sentence_end))
            return header, footer, bool(anchored)

        def score(group):
            chars = sum(len(_clean(line.text)) for _, line in group)
            return 0.45 * min(1, chars / 90) + 0.35 + 0.20 * min(1, len(group) / 2)

        candidates = [(group, *anchors(group)) for group in groups]
        anchored = [item for item in candidates if item[3]]
        best, (speaker, speaker_box), continue_box, has_anchor = max(
            anchored or candidates,
            key=lambda item: (bool(item[1][0]) + bool(item[2]), score(item[0])),
        )
        boxes = [line.box for _, line in best]
        paragraph = _union(boxes)
        layout = "inventory_left" if paragraph.cx < self.capture_width * 0.48 else "normal_right"
        confidence = min(0.99, score(best) + 0.08 * bool(speaker) + 0.08 * bool(continue_box))
        detected = has_anchor and confidence >= 0.62
        reasons = [f"seed_lines={len(seeds)}", f"group_lines={len(best)}", f"layout={layout}"]
        if speaker:
            reasons.append("known_speaker_found")
        if continue_box:
            reasons.append("continue_cue_found")
        if not has_anchor:
            reasons.append("no_dialogue_anchor")
        return DialogueContext(
            detected, layout, confidence, speaker,
            " ".join(_clean(line.text) for _, line in best) if detected else "",
            paragraph if detected else None,
            source_line_indexes=sorted({i for i, _ in best}) if detected else [],
            reasons=reasons, speaker_box=speaker_box if detected else None,
            continue_box=continue_box if detected else None,
        )
