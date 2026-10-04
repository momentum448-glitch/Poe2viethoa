# POE2 Việt Hóa — HANDOFF_CURRENT

**Updated:** 2026-10-04

## Current phase

**Phase 0 — Spike 001: PoE2 Signal Audit**

## Locked decisions

- Repository: `momentum448-glitch/Poe2viethoa`.
- Goal: modular PoE2 Vietnamese localization engine, not dialogue-only forever.
- First module: Story Dialogue.
- Alpha is for the primary user first; architecture should remain suitable for later community release.
- Runtime: offline, pretranslated data.
- Safety boundary: screen/log based; no RAM reading, injection, hooking, game-file modification, or automated game input in this engine direction.
- Normal overlay target: cover English text and replace it with Vietnamese.
- Uncertain matches: hidden in Normal mode; visible as candidates only in Debug mode.
- Translation source: reviewable text files in Git; runtime SQLite remains a planned build artifact, not yet implemented.
- Alpha updates manually; automatic updater later.
- Python first, packaged EXE after Local Alpha passes.

## Research findings influencing architecture

1. RuneHelper demonstrates production-quality PoE2 OCR scheduling:
   frame-change detection, stability gates, OCR cache, confidence filtering and diagnostic dumps.
2. MaxOverlay-POE2 validates MSS + Windows OCR + positional text + indexed fuzzy matching on PoE2.
3. Exile-UI reads `Client.txt` for area transitions and dialogue-derived signals.
4. Replacement-style overlays exist in generic screen translators.
5. PoE2 Turkish localization projects demonstrate glossary + translation-memory workflows that survive row reordering after patches.

## Open architectural decision

Dialogue text source:

- A: Log-first
- B: OCR-first
- C: Hybrid log + OCR

Pre-test recommendation: **C Hybrid**.

Do not lock until Spike 001 evidence exists.

## Current execution

Repository initialized with:

- README
- PROJECT_GUIDE
- HANDOFF_CURRENT
- Spike 001 documentation
- Spike setup/run scripts
- Spike Python probe
- dependency list

## Next checkpoint

Run Spike 001 against a real PoE2 NPC conversation and inspect:

- whether exact story dialogue appears in Client.txt;
- stable areaId events;
- OCR text accuracy;
- OCR word/line bounding boxes;
- dialogue layout changes.

Then lock the Dialogue signal architecture and begin Phase 1 implementation.


## Spike 001 result — first real QC

Session: `20261004_134633`

- Windows OCR available and functioning.
- Capture: 1920x1080 primary monitor, ROI 1267x302.
- OCR successfully captured at least 10 distinct Renly story dialogue lines with line/word bounding boxes.
- Two stable dialogue horizontal layouts were observed, consistent with normal vs inventory-open states.
- Main OCR contamination came from chat/UI text outside the dialogue panel, which supports adding panel/context filtering before matching.
- `Client.txt` was not auto-detected in this run, so Log-first vs Hybrid is **not yet decided**.
- Spike 001B added to locate the active PoE2 installation from the running process and inspect the recent Client.txt tail without requiring another full NPC test.

Next: run `QC_LOG_ONLY.bat` while PoE2 is open, send `QC_LOG_RESULT_*.zip`, then lock Dialogue signal architecture.


## Architecture Decision — 2026-10-04

### Dialogue signal source: OCR-FIRST — LOCKED

Evidence from real QC:

- Spike 001 captured at least 10 distinct Renly story-dialogue lines through Windows OCR.
- OCR returned usable word/line bounding boxes.
- Both normal dialogue layout and inventory-open shifted layout were observed and readable.
- Main OCR noise came from nearby chat/UI text, so Phase 1 must add dialogue-panel/layout filtering before matching.
- Spike 001B/V4/V5 repeatedly failed to locate a reliable `Client.txt` on the test machine.
- V5 did detect a running `PathOfExile.exe` process and Steam root `E:\Steam`, but found no usable PoE2 manifest/log path.

Decision:

```text
Screen
  ↓
Dialogue layout detector
  ↓
Frame stability gate
  ↓
Windows OCR + bounding boxes
  ↓
Text stabilizer
  ↓
Context resolver
  ↓
Candidate index
  ↓
Exact → fuzzy matcher
  ↓
Translation
  ↓
Replacement overlay
```

`Client.txt` is now optional future context only. Do not block development on it.

### Phase transition

Phase 0 signal validation is complete.
Next: **Phase 1 — Core Capture + Dialogue Context**.


## Phase 1 implementation — 2026-10-04

### Implemented

- `app/models.py`: shared Rect/OCR/DialogueContext models.
- `app/capture.py`: MSS capture with a resolution-scaled dialogue ROI.
- `app/frame_stabilizer.py`: sampled BGRA frame-change detector and settle gate.
- `app/ocr_windows.py`: Windows Media OCR adapter returning line/word bounding boxes.
- `app/dialogue_context.py`: dialogue cluster detector and normal/inventory layout classification.
- `app/game_window.py`: Win32 foreground guard; capture pauses when PoE2 is not foreground.
- `app/phase1_probe.py`: real Phase 1 diagnostic runner.
- `tests/`: unit tests for frame stabilization and dialogue context.
- `QC_PHASE1.bat`: one-click setup, tests, 90s real-game QC, automatic result ZIP.

### Calibration performed from existing real QC evidence

The dialogue detector was replayed conceptually against the existing Renly OCR evidence before requesting another user QC.

Corrections made:

- removed false positives from NPC topic-selection UI;
- removed ESC/menu sentence-shaped false positives;
- excluded global chat at the bottom of the capture ROI;
- required a dialogue anchor: upper speaker label and/or `Continue`;
- preserved short wrapped tail lines such as one-word/short sentence endings;
- retained both observed horizontal layouts.

### Current checkpoint

Phase 1 source implementation is complete enough for real-game QC.

Next action: user runs `QC_PHASE1.bat` and sends `QC_PHASE1_RESULT_*.zip`.

Pass criteria:

1. no OCR activity while POE2 is not foreground;
2. OCR call count is substantially lower than capture count;
3. real story lines are detected while topic/ESC/chat screens are rejected;
4. normal and inventory-open layouts classify correctly;
5. no repeated OCR loop on a completely unchanged dialogue frame.

If pass: lock Phase 1 and begin Phase 2 — Dialogue Matching + Translation Store.
