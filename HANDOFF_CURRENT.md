# POE2 Việt Hóa — HANDOFF_CURRENT

**Updated:** 2026-10-04

## Current phase

**Phase 1 — Core Capture + Dialogue Context**  
Status: implemented, awaiting real-game QC.

## Locked decisions

- Repository: `momentum448-glitch/Poe2viethoa`.
- Goal: modular PoE2 Vietnamese localization engine, starting with Story Dialogue.
- Architecture: **OCR-first**.
- `Client.txt` is optional future context only, not a runtime dependency.
- Runtime: local, offline, pretranslated data.
- No RAM reading, injection, hooking, game-file modification, or automated game input.
- Normal overlay target: cover English text and replace it with Vietnamese.
- Uncertain matches: hidden in Normal mode; candidates may appear only in Debug mode.
- Translation source stays reviewable in Git; runtime SQLite may be built later.
- Python first; packaged EXE after Local Alpha passes.
- Current QC duration: **60 seconds**.

## Evidence behind OCR-first

Real QC at 1920×1080 showed:

- Windows OCR captured at least 10 distinct Renly story-dialogue lines.
- OCR returned usable word/line bounding boxes.
- Both normal and inventory-open shifted layouts were readable.
- OCR noise mainly came from nearby chat/UI and is addressable with panel/context filtering.
- Repeated log probes did not produce a reliable `Client.txt` path on the test machine.

Decision flow:

```text
Screen
  ↓
Dialogue layout detector
  ↓
Frame stability gate
  ↓
Windows OCR + bounding boxes
  ↓
Text/context cleanup
  ↓
Candidate index
  ↓
Exact → fuzzy matcher
  ↓
Translation
  ↓
Replacement overlay
```

## Phase 1 implemented

- `app/models.py`
- `app/capture.py`
- `app/frame_stabilizer.py`
- `app/ocr_windows.py`
- `app/dialogue_context.py`
- `app/game_window.py`
- `app/phase1_probe.py`
- `tests/`
- `QC_PHASE1.bat`

Detector calibration includes:

- reject NPC topic-selection UI;
- reject ESC/menu sentence-shaped false positives;
- exclude bottom chat noise;
- require dialogue anchor: speaker and/or `Continue`;
- preserve short wrapped tail lines;
- classify normal vs inventory-open horizontal layouts.

## Repository cleanup

Obsolete Spike 001 scripts, log-only probes, old QC launchers, and their old setup/docs were removed. The only user-facing QC entry point is now:

```text
QC_PHASE1.bat
```

## Next checkpoint

User runs `QC_PHASE1.bat` and sends `QC_PHASE1_RESULT_*.zip`.

Pass criteria:

1. no OCR activity while POE2 is not foreground;
2. OCR calls are substantially fewer than captures;
3. story lines are detected while topic/ESC/chat screens are rejected;
4. normal and inventory-open layouts classify correctly;
5. unchanged dialogue does not repeatedly trigger OCR;
6. no recurring OCR exceptions.

If Phase 1 passes: begin **Phase 2 — Dialogue Matching + Translation Store**.
