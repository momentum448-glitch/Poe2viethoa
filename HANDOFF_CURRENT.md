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
