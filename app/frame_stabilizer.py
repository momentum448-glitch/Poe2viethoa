from __future__ import annotations

from dataclasses import dataclass
import time


@dataclass(frozen=True)
class StabilizerDecision:
    should_ocr: bool
    changed_fraction: float
    stable_frames: int
    dirty_since_ocr: bool
    reason: str


class FrameStabilizer:
    """Cheap sampled-frame stability gate.

    It intentionally works on raw BGRA bytes so the capture loop does not need
    numpy. Only every Nth pixel is sampled.

    Important invariant: once OCR has consumed a settled frame, unchanged
    frames do *not* trigger OCR again. A new visual change must happen first.
    """

    def __init__(
        self,
        *,
        sample_stride: int = 8,
        channel_threshold: int = 10,
        changed_fraction_threshold: float = 0.003,
        stable_frames_required: int = 2,
        min_ocr_interval_ms: int = 500,
        max_wait_ms: int = 1500,
    ) -> None:
        self.sample_stride = max(1, sample_stride)
        self.channel_threshold = max(0, channel_threshold)
        self.changed_fraction_threshold = max(0.0, changed_fraction_threshold)
        self.stable_frames_required = max(1, stable_frames_required)
        self.min_ocr_interval_ms = max(0, min_ocr_interval_ms)
        self.max_wait_ms = max(self.min_ocr_interval_ms, max_wait_ms)

        self._previous: bytes | None = None
        self._stable_frames = 0
        self._last_ocr_at = 0.0
        self._last_change_at = time.monotonic()
        self._dirty_since_ocr = True

    def reset(self) -> None:
        self._previous = None
        self._stable_frames = 0
        self._last_ocr_at = 0.0
        self._last_change_at = time.monotonic()
        self._dirty_since_ocr = True

    def mark_ocr(self, now: float | None = None) -> None:
        self._last_ocr_at = time.monotonic() if now is None else now
        self._dirty_since_ocr = False

    def observe(self, bgra: bytes, *, now: float | None = None) -> StabilizerDecision:
        now = time.monotonic() if now is None else now

        if self._previous is None or len(self._previous) != len(bgra):
            self._previous = bytes(bgra)
            self._stable_frames = 0
            self._last_change_at = now
            self._dirty_since_ocr = True
            return StabilizerDecision(False, 1.0, 0, True, "first_frame")

        changed_fraction = self._sampled_changed_fraction(self._previous, bgra)
        changed = changed_fraction >= self.changed_fraction_threshold

        if changed:
            self._stable_frames = 0
            self._last_change_at = now
            self._dirty_since_ocr = True
        else:
            self._stable_frames += 1

        self._previous = bytes(bgra)

        if not self._dirty_since_ocr:
            return StabilizerDecision(
                False,
                changed_fraction,
                self._stable_frames,
                False,
                "unchanged_since_ocr",
            )

        since_ocr_ms = (now - self._last_ocr_at) * 1000.0 if self._last_ocr_at else 10**9
        since_change_ms = (now - self._last_change_at) * 1000.0

        if since_ocr_ms < self.min_ocr_interval_ms:
            return StabilizerDecision(
                False,
                changed_fraction,
                self._stable_frames,
                True,
                "ocr_cooldown",
            )

        if self._stable_frames >= self.stable_frames_required:
            return StabilizerDecision(
                True,
                changed_fraction,
                self._stable_frames,
                True,
                "settled",
            )

        if since_change_ms >= self.max_wait_ms:
            return StabilizerDecision(
                True,
                changed_fraction,
                self._stable_frames,
                True,
                "max_wait",
            )

        return StabilizerDecision(
            False,
            changed_fraction,
            self._stable_frames,
            True,
            "waiting_for_settle",
        )

    def _sampled_changed_fraction(self, previous: bytes, current: bytes) -> float:
        step = 4 * self.sample_stride
        changed = 0
        samples = 0
        threshold = self.channel_threshold

        for i in range(0, min(len(previous), len(current)) - 3, step):
            # BGRA. Alpha is ignored.
            db = abs(previous[i] - current[i])
            dg = abs(previous[i + 1] - current[i + 1])
            dr = abs(previous[i + 2] - current[i + 2])
            if max(db, dg, dr) > threshold:
                changed += 1
            samples += 1

        return 0.0 if samples == 0 else changed / samples
