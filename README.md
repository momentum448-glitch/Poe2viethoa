# POE2 Việt Hóa

Local-first Vietnamese localization engine for Path of Exile 2.

## Current phase

**Phase 2 — Dialogue Matching + Fresh Translation Store**

Phase 1 (capture/OCR/context) is **PASS / LOCKED**.

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
```

## No old project data

The current project does **not** use the previous `Translate PJ` dictionary and does not require Remote Desktop.

Fresh dialogue source is recreated locally from pinned public 2026 upstream snapshots:

- English table output: `addohm/poe2-en-cn-dict`
- optional speaker/topic enrichment: `fireMCG/Exiled-Vault`

Raw upstream English text is downloaded only into gitignored `source_data/`. It is not committed to this repository.

Pinned versions live in:

```text
sources/sources.lock.json
```

## Current QC

Download the repo, extract it, open PoE2, then run:

```text
QC_PHASE2.bat
```

The launcher automatically:

1. prepares Python environment;
2. runs unit tests;
3. syncs the fresh source corpus;
4. builds `runtime/translations.sqlite3`;
5. runs a 60-second end-to-end matcher QC;
6. creates `QC_PHASE2_RESULT_*.zip`.

QC safety behavior:

- the 60-second timer counts only while PoE2 is the foreground app;
- Alt+Tab pauses the timer;
- another foreground application is never captured or OCRed;
- fuzzy results that are nearly tied with another candidate are hidden from Normal mode.

For the current Alpha corpus, test one or more of:

- Renly → **Introduction**
- Renly → **The Miller**
- Una → **Home**
- Una → **Clearfell**

Send the generated ZIP back to the project chat.

## Fresh Alpha translations

The initial Phase 2 corpus contains 9 newly-created Vietnamese segments derived from the pinned 2026 source plus real OCR evidence from the Phase 1 QC.

They are stored without raw English text in:

```text
translations/dialogue_vi.json
```

## Project principles

- GitHub is the source of truth.
- Runtime is local and offline.
- No RAM reading, DLL injection, game hooking, game-file modification, or automated game input.
- OCR-first for Story Dialogue.
- `Client.txt` is optional future context only.
- Normal overlay will cover English and replace it with Vietnamese.
- Low-confidence and ambiguous fuzzy matches are hidden in Normal mode.
- Raw source data, runtime caches and generated DBs are not committed.
- Python first; packaged EXE after Local Alpha passes.

## Developer tests

```bat
run_tests.bat
```

## Useful build command

To refresh source/build data without running QC:

```text
SOURCE_SYNC.bat
```
