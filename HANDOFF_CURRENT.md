# POE2 Việt Hóa — HANDOFF_CURRENT

**Updated:** 2026-10-04

## Current phase

**Phase 2 — Dialogue Matching + Fresh Translation Store**

Phase 1 is **PASS / LOCKED**.

## Locked product decisions

- Repository: `momentum448-glitch/Poe2viethoa`.
- Goal: modular PoE2 Vietnamese localization engine, starting with Story Dialogue.
- Dialogue signal: **OCR-first**.
- Runtime: local/offline, pretranslated data.
- No RAM reading, injection, hooking, game-file modification, or automated game input.
- `Client.txt` is optional future context only.
- Normal overlay target: cover English and replace it with Vietnamese.
- Low-confidence matches are hidden in Normal mode.
- Translation source is reviewable in Git; generated runtime DB is local.
- User-facing QC defaults to **60 seconds**.
- **Do not use Remote Desktop for source recovery.**
- **Do not use the previous project dictionary or old 208-line corpus.**

## Phase 1 final QC — PASS

Session: `20261004_163219`

- captures: 461
- visual changes: 54
- OCR calls: 53
- dialogue detections: 17
- normal-right: 7
- inventory-left: 10
- OCR errors: 0
- foreground pauses: 0
- elapsed: 60.06 s

Real Renly/Una story lines were detected. Topic menus, waypoint/proclamation and unrelated UI were rejected.

## Phase 2 implemented

- `app/text_normalize.py`
- `app/text_stabilizer.py`
- `app/translation_models.py`
- `app/translation_store.py`
- `app/matcher.py`
- `app/dialogue_pipeline.py`
- `app/phase2_probe.py`
- `tools/build_translation_db.py`
- `tools/source_sync.py`
- `SOURCE_SYNC.bat`
- `QC_PHASE2.bat`
- matcher/store/source-sync unit tests

Matcher policy:

```text
OCR dialogue
  ↓
Text Stabilizer / dedupe
  ↓
Normalize
  ↓
Exact match
  ↓ miss
Inverted-token candidate index
  ↓
RapidFuzz fallback
  ↓
High / Medium / Low confidence
```

## Fresh-source architecture

Old project data has been abandoned.

Pinned source lock:

```text
sources/sources.lock.json
```

Primary English source:
- `addohm/poe2-en-cn-dict`
- pinned commit `28d683c99600eb407b4e014ccaf8247532fb4607`
- uses `NPCTextAudio` and `NPCTalkDialogueTextAudio` English output
- contains `<continue>` boundaries matching actual on-screen dialogue pages

Optional speaker/topic enrichment:
- `fireMCG/Exiled-Vault`
- pinned commit `b3dd7457aa4e7f126021b8d8577f38ef205490c7`
- 2026-09-30 snapshot
- context enrichment is optional; source sync continues if this dependency is unavailable

Raw upstream material is downloaded into gitignored `source_data/` and is not committed.

Source segments receive deterministic IDs from table + normalized-English SHA-256 fingerprint.

Committed Vietnamese file:

```text
translations/dialogue_vi.json
```

It contains only `source_id + vi + review state`, not the upstream English corpus.

Runtime build joins:

```text
source_data/dialogue_corpus.jsonl
        +
translations/dialogue_vi.json
        ↓
runtime/translations.sqlite3
```

Build fails if a Vietnamese `source_id` no longer exists in the synced source corpus.

## Fresh-source validation already performed

Nine unique Renly/Una dialogue segments captured by real Phase 1 OCR were checked against the pinned 2026 English source.

All 9 were found.

Examples of matched source records included:
- Renly introduction
- Renly / The Miller
- Una / Home
- Una / Clearfell

The 2026 source correctly retains `<continue>` boundaries. This also fixed a truncation found in an older 2025 public dump, confirming the project should not rely on that older dump.

## Fresh Alpha Vietnamese corpus

Nine Vietnamese translations were recreated from the fresh source and Phase 1 evidence. They were not copied from the old project data.

Current QC coverage:
- Renly → Introduction
- Renly → The Miller
- Una → Home
- Una → Clearfell

## Next checkpoint

User downloads a fresh repo copy and runs:

```text
QC_PHASE2.bat
```

The launcher performs source sync, DB build and a 60-second end-to-end matcher QC.

Expected output:

```text
QC_PHASE2_RESULT_YYYYMMDD_HHMMSS.zip
```

Pass criteria:

1. source sync completes;
2. all committed Alpha translation IDs resolve;
3. runtime DB builds with 9 records;
4. text dedupe suppresses repeated OCR of the same visible sentence;
5. at least one Alpha dialogue produces a high-confidence Vietnamese match;
6. OCR/runtime errors = 0.

If pass: lock Phase 2 and begin **Phase 3 — Replacement Overlay**.
