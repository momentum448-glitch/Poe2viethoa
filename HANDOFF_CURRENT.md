# POE2 Việt Hóa — HANDOFF_CURRENT

**Updated:** 2026-10-04

## Current phase

**Phase 2 — Dialogue Matching + Translation Store**

Phase 1 is **PASS / LOCKED**.

## Locked decisions

- Repository: `momentum448-glitch/Poe2viethoa`.
- Goal: modular PoE2 Vietnamese localization engine, starting with Story Dialogue.
- Dialogue architecture: **OCR-first**.
- `Client.txt` is optional future context only, not a runtime dependency.
- Runtime: local, offline, pretranslated data.
- No RAM reading, injection, hooking, game-file modification, or automated game input.
- Normal overlay target: cover English text and replace it with Vietnamese.
- Uncertain matches: hidden in Normal mode; candidates may appear only in Debug mode.
- Translation source stays reviewable in Git; runtime SQLite can be generated as a build artifact.
- Python first; packaged EXE after Local Alpha passes.
- User-facing QC windows should default to **60 seconds** unless a shorter focused test is sufficient.

## Phase 1 architecture — LOCKED

```text
PoE2 screen
  ↓
Foreground guard
  ↓
Dialogue capture ROI
  ↓
Frame stabilizer / bounded OCR scheduler
  ↓
Windows OCR + word/line bbox
  ↓
Dialogue context detector
  ↓
normal_right / inventory_left / not-dialogue
```

## Phase 1 final real QC

Session: `20261004_163219`

Results:

- captures: **461**
- visual changes: **54**
- OCR calls: **53**
- dialogue detections: **17**
- normal-right detections: **7**
- inventory-left detections: **10**
- OCR errors: **0**
- foreground transient losses: **0**
- foreground pauses: **0**
- elapsed: **60.06 s**
- result: **PASS**

Observed dialogue included multiple real Renly and Una story lines.

Observed rejection behavior:

- NPC topic-selection screens were not accepted as story dialogue;
- non-dialogue world/UI text was rejected;
- waypoint/proclamation screens were rejected;
- unrelated lower-screen/UI text did not become dialogue output.

OCR timing in this session was roughly ~15 ms per call on average.

## Known Phase 1 behavior carried into Phase 2

Animated game backgrounds can cause OCR to run again while the same dialogue sentence remains visible. In the final QC, some identical dialogue texts appeared 2–3 times.

This is acceptable at the capture/OCR layer because:

- OCR calls remain bounded to about ~1 Hz under continuous animation;
- OCR cost is low;
- no OCR exceptions occurred.

Phase 2 must add a **Text Stabilizer / OCR cache** before matching so duplicate normalized dialogue does not trigger repeated matcher/overlay work.

## Phase 2 target flow

```text
DialogueContext.text
    ↓
Text Stabilizer / dedupe
    ↓
Normalization
    ↓
Candidate index
    ↓
Exact match
    ↓ fallback
Fuzzy match
    ↓
Confidence policy
    ↓
Translation Store
    ↓
TranslationResult
```

## Phase 2 first implementation tasks

1. normalized-text dedupe with speaker/layout awareness;
2. translation record schema;
3. human-readable JSON source store;
4. build step to runtime SQLite;
5. candidate inverted index;
6. exact-first matching;
7. fuzzy fallback + confidence bands;
8. unit tests using real OCR distortions observed in Phase 1.

## Next checkpoint

Build Phase 2 against the real OCR evidence already collected.

No additional Phase 1 QC is required.
