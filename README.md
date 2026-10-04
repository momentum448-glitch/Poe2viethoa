# POE2 Việt Hóa

Local-first Vietnamese localization engine for Path of Exile 2.

## Current phase

**Phase 3 — Replacement Overlay**

Phase 1 and Phase 2 are **PASS / LOCKED**.

Current flow:

```text
PoE2 screen
  ↓
Foreground guard
  ↓
Dialogue ROI
  ↓
Frame scheduler
  ↓
Windows OCR + bbox
  ↓
Dialogue detector
  ↓
Text dedupe
  ↓
Exact / fuzzy matcher
  ↓
Ambiguity guard
  ↓
Fresh source corpus
  ↓
Vietnamese translation
  ↓
Replacement overlay
```

## Current QC

Download/extract a fresh repo copy, open PoE2, then run:

```text
QC_PHASE3.bat
```

Recommended Alpha topics:
- Renly → **Introduction**
- Renly → **The Miller**
- Una → **Home**
- Una → **Clearfell**

When a High-confidence translation is found, the Phase 3 proof should:
- cover the English dialogue text;
- draw Vietnamese at the OCR-derived position;
- stay click-through/topmost;
- disappear when PoE2 is not foreground;
- stay excluded from OCR capture so it does not read itself.

The QC runs for 60 seconds of active PoE2 foreground time and creates:

```text
QC_PHASE3_RESULT_*.zip
```

Send that ZIP back to the project chat.

## Phase 2 QC result

Final Phase 2 real-game QC: **PASS**.

Session `20261004_175216`:
- 54 OCR calls;
- 16 dialogue detections;
- 6 duplicate suppressions;
- 5 High matches;
- 0 OCR/runtime errors;
- 60.00 seconds active game time.

The observed MISS lines were valid untranslated Renly dialogue, not false UI matches.

## Fresh-source policy

The project does **not** use the previous project dictionary and does not require Remote Desktop.

Fresh dialogue source is recreated locally from pinned public snapshots:
- `addohm/poe2-en-cn-dict`
- optional context: `fireMCG/Exiled-Vault`

Raw upstream English text stays in gitignored `source_data/`.

Vietnamese work is stored in:

```text
translations/dialogue_vi.json
```

## Project principles

- GitHub is the source of truth.
- Runtime is local and offline.
- No RAM reading, DLL injection, game hooking, game-file modification, or automated game input.
- OCR-first for Story Dialogue.
- `Client.txt` is optional future context only.
- Normal overlay covers English and replaces it with Vietnamese.
- Low-confidence and ambiguous fuzzy matches are hidden in Normal mode.
- Raw source data, runtime caches and generated DBs are not committed.
- Python first; package an EXE after Local Alpha stabilizes.
