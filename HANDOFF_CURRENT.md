# POE2 Việt Hóa — HANDOFF_CURRENT

**Updated:** 2026-10-04

## Current phase

**Phase 3 — Replacement Overlay**

Phase 1 and Phase 2 are **PASS / LOCKED**.

## Locked product decisions

- Repository: `momentum448-glitch/Poe2viethoa`.
- Goal: modular PoE2 Vietnamese localization engine, starting with Story Dialogue.
- Dialogue signal: **OCR-first**.
- Runtime: local/offline, pretranslated data.
- No RAM reading, injection, hooking, game-file modification, or automated game input.
- `Client.txt` is optional future context only.
- Normal overlay target: cover English and replace it with Vietnamese.
- Low-confidence and ambiguous fuzzy matches are hidden in Normal mode.
- Translation source is reviewable in Git; generated runtime DB is local.
- User-facing QC defaults to **60 seconds of active PoE2 foreground time**.
- Diagnostics must not capture/OCR another foreground application.
- **Do not use Remote Desktop for source recovery.**
- **Do not use the previous project dictionary or old 208-line corpus.**

## Phase 1 final QC — PASS / LOCKED

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

## Phase 2 final QC — PASS / LOCKED

Session: `20261004_175216`

- captures: 471
- OCR calls: 54
- dialogue detections: 16
- text emitted: 10
- duplicates suppressed: 6
- matched High: 5
- matched Medium: 0
- unmatched: 5
- normal-right: 4
- inventory-left: 12
- OCR errors: 0
- foreground transient losses: 12
- foreground pauses: 1
- active game time: 60.00 s
- wall time: 64.41 s
- result: `PASS`

Verified matched dialogue:
- Renly / The Miller segment 1
- Renly / The Miller segment 2
- Renly / Introduction segment 1
- Renly / Introduction segment 2
- Renly / Introduction segment 3

All five matched at exact/high confidence 100%.

The five MISS lines inspected in the QC pack were valid Renly dialogue not yet included in the nine-line Alpha translation corpus. They were not false-positive UI detections.

Phase 2 behavior verified:
- active-time timer pauses outside PoE2;
- no OCR/runtime errors;
- text dedupe suppresses repeated visible dialogue;
- exact/high matches resolve to Vietnamese;
- untranslated dialogue stays hidden rather than displaying a wrong translation.

## Fresh-source architecture — LOCKED

Pinned source lock:

```text
sources/sources.lock.json
```

Primary English source:
- `addohm/poe2-en-cn-dict`
- pinned commit `28d683c99600eb407b4e014ccaf8247532fb4607`
- uses `NPCTextAudio` and `NPCTalkDialogueTextAudio`
- preserves `<continue>` on-screen page boundaries

Optional speaker/topic enrichment:
- `fireMCG/Exiled-Vault`
- pinned commit `b3dd7457aa4e7f126021b8d8577f38ef205490c7`

Raw source is downloaded only into gitignored `source_data/`.

Committed Vietnamese work:

```text
translations/dialogue_vi.json
```

Runtime build:

```text
source_data/dialogue_corpus.jsonl
        +
translations/dialogue_vi.json
        ↓
runtime/translations.sqlite3
```

The Alpha corpus currently contains 9 reviewed Vietnamese segments.

## Phase 3 implementation started

Added:
- `app/replacement_overlay.py`
- `app/phase3_probe.py`
- `tests/test_replacement_overlay.py`
- `QC_PHASE3.bat`

Current Phase 3 proof design:
- topmost Windows overlay;
- click-through / no activation;
- OCR bbox → absolute screen rectangle;
- mask English text with a sampled dark panel color;
- render Vietnamese using Segoe UI with pixel-width wrapping and font shrink;
- per-monitor DPI awareness;
- clear overlay when PoE2 loses foreground;
- only High-confidence matches display;
- unmatched/Medium/Low results hide the overlay;
- use `SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE)` so runtime OCR does not read the Vietnamese overlay back into itself;
- QC-only overlay proof screenshots temporarily allow capture without running OCR on those frames.

## Current open risks for Phase 3 QC

Must be verified on the real Windows/PoE2 session:
1. Tk/Win32 overlay appears above the actual PoE2 presentation mode;
2. click-through does not steal mouse/keyboard focus;
3. physical-pixel coordinates align under the user's Windows DPI setting;
4. `WDA_EXCLUDEFROMCAPTURE` works on the user's Windows 10 build with MSS;
5. replacement mask blends acceptably with PoE2's textured dialogue panel;
6. Vietnamese wrapping/font size is readable and does not cover the Continue button.

## Next checkpoint

User downloads a fresh repo copy and runs:

```text
QC_PHASE3.bat
```

Recommended Alpha topics:
- Renly → Introduction
- Renly → The Miller
- Una → Home
- Una → Clearfell

Expected behavior:
- when a High match is found, English dialogue text is covered and Vietnamese is shown;
- Alt+Tab clears overlay and pauses the 60-second active timer;
- game input remains unaffected.

Expected output:

```text
QC_PHASE3_RESULT_YYYYMMDD_HHMMSS.zip
```

Phase 3 PASS requires:
1. at least one High match;
2. at least one visible overlay update;
3. at least one QC overlay proof screenshot;
4. OCR errors = 0;
5. overlay errors = 0;
6. no self-capture loop;
7. visual placement/readability acceptable on real PoE2.

If Phase 3 passes, proceed to **Phase 4 — Local Alpha packaging/runtime UX**.
