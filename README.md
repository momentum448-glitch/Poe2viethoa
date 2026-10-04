# POE2 Việt Hóa

Local-first Vietnamese localization engine for Path of Exile 2.

## Current phase

**Phase 1 — Core Capture + Dialogue Context**

Architecture decision from real QC: **OCR-first**.

Current runtime probe now includes:

- foreground POE2 guard;
- screen capture via MSS;
- frame-change / stability gate;
- Windows Media OCR;
- OCR word + line bounding boxes;
- dialogue-vs-UI filtering;
- normal vs inventory-open layout classification;
- diagnostics bundle for QC.

## QC Phase 1

1. Download the repo ZIP.
2. Extract it.
3. Open Path of Exile 2 and stand near a story NPC.
4. Double-click **`QC_PHASE1.bat`**.
5. During the 90-second probe:
   - talk through 3–5 story lines;
   - keep each line visible briefly;
   - if convenient, test part of the conversation with inventory closed and part with inventory open;
   - leave POE2 in the foreground while the probe is reading.
6. Let the probe finish by itself.

It will create:

```text
QC_PHASE1_RESULT_YYYYMMDD_HHMMSS.zip
```

Send that ZIP back to the project chat.

## Architecture

```text
PoE2 screen
    ↓
Foreground game guard
    ↓
Dialogue capture ROI
    ↓
Frame-change / stability gate
    ↓
Windows OCR + bounding boxes
    ↓
Dialogue context detector
    ↓
[Phase 2]
Candidate index → Exact/Fuzzy match → Translation
    ↓
[Phase 3]
Replacement overlay
```

## Project principles

- GitHub is the source of truth.
- Runtime is local and offline.
- No process-memory reading, DLL injection, game hooking, or automated game input.
- Start with Story Dialogue, but keep the engine modular for Quest, Tutorial, UI, Skill/Passive, Item and Mechanics.
- `Client.txt` is optional future context only, not a runtime dependency.
- Translation source data stays human-readable in Git; runtime formats can be built from it later.

## Developer tests

```bat
run_tests.bat
```

## Historical probes

Spike 001 and the log-only probes remain in the repository as research evidence. New QC should use **`QC_PHASE1.bat`**.
