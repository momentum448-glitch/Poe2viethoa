# POE2 Việt Hóa — HANDOFF_CURRENT

**Updated:** 2026-10-04

## Current phase

**Phase 3 — Replacement Overlay: technical and visual QC PASS**

Phase 1 and Phase 2 are **PASS / LOCKED**.
Next planned phase: **Phase 4 — Local Alpha packaging/runtime UX**.

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

## Phase 3 implementation

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

## Phase 3 pre-QC code review — 2026-10-04

User requested another error review before running the proof.

Fixed:
1. Native styles and capture affinity now target Tk's actual top-level wrapper HWND,
   not its child HWND. Win32 argument/return types preserve 64-bit handles.
2. Overlay stays topmost with `SWP_NOACTIVATE`; the native styles and affinity
   are checked. Windows builds older than 19041 stop with a diagnostic ZIP.
3. The mask covers the full English OCR bounding box, even when Vietnamese is
   shorter or the source is wider/taller than the old 520×108 limit. The actual
   OCR Continue position bounds the mask when available.
4. Vietnamese uses pixel-sized fonts. Complete text must fit within the mask;
   long words wrap, and overflow is hidden/reported instead of spilling into controls.
5. Fast Alt+Tab and closing/reopening the same dialogue reset display/dedupe state.
   A confirmed non-dialogue result or OCR error clears stale translations.
6. Foreground is checked around capture, after async OCR, and around QC proof
   capture. A skipped proof is retried later; failed affinity restoration stops capture.
7. Runtime/setup failures and graceful interruptions close resources and package
   partial diagnostics. The launcher shows the ZIP path on probe failure too.
8. Automatic success is `TECHNICAL_PASS`, with `visual_qc_required=true`.
   It does not lock Phase 3 or advance to Phase 4 without real-game visual QC.

Validation:
- 47 automated tests passed on Linux/Python 3.12, including simulated Win32/Tk
  boundaries and complete probe lifecycle tests.
- Replayed all 16 detected dialogue bounding boxes from latest user QC
  `20261004_175216`: 16/16 masks cover the complete English bounding box.
- No Remote Desktop and no previous project dictionary/corpus were used.
- Native Windows/Tk/MSS/PoE2 integration and visual readability remain unverified
  until the next user QC pack. The automated tests use mocks for those platform boundaries.

## Phase 3 real-game QC — technical and visual PASS

Session: `20261004_183317`

Evidence: `QC_PHASE3_RESULT_20261004_183317.zip`, supplied by the user and reviewed
from its local attachment. SHA-256:
`ee02f505ab3e7be7717c91646bc101bea9dae89da834496d74e854eb7cd272f6`.
Raw logs/screenshots remain outside Git. The pack does not record a code revision.

- platform: Windows, Python 3.12.10, 64-bit;
- monitor: 1920×1080; OCR region: left 230, top 421, width 1190, height 270;
- runtime translation records: 9;
- captures: 467;
- OCR calls: 53;
- dialogue detections: 25 (normal-right 17, inventory-left 8);
- text emitted: 9;
- duplicates suppressed: 16;
- matched High: 6, all exact at 100%; matched Medium: 0;
- unmatched: 3;
- overlay updates: 6; overlay clears: 2; unique proof screenshots: 5;
- OCR / overlay / runtime errors: 0 / 0 / 0;
- foreground transient losses: 24; foreground pauses: 2;
- active game time: 60.00 s; wall time: 76.50 s;
- automatic result: `TECHNICAL_PASS`; stop reason: `completed`.

Manual review:
1. All five proof images show the Vietnamese replacement above the real PoE2
   dialogue panel. Normal-right and inventory-left placement are both represented.
2. Vietnamese is complete and readable at 18–20 px, with no clipped text,
   exposed English fragments or overlap with Continue. The dark mask is acceptable
   for this Alpha proof, although its solid rectangle remains visible on the texture.
3. All six logged masks contain the complete English OCR bounding box.
4. The same Introduction segment moves from normal-right to inventory-left at
   event 17 and triggers a fresh overlay update on `context_changed`.
5. Later OCR screenshots at events 4 and 18 still show English while the overlay
   is logged visible. Repeated detections remain exact/duplicates rather than
   Vietnamese, supporting working capture exclusion and no observed self-capture loop.
6. Menu transitions at events 10 and 25 log `hide_no_dialogue`. The three MISS
   screenshots at events 43, 46 and 48 show real Renly dialogue, not unrelated UI;
   each is absent from the nine-segment Alpha translations and logs `hide_unmatched`.

The real Windows run and manual screenshot review pass the technical and visual
checkpoint on this setup. This is not a claim of complete game localization.
The nine reviewed segments are unchanged; no dictionary from the previous project
was used.

## Remaining validation scope

- A screenshot pack cannot directly verify that mouse/keyboard focus remains
  unaffected or establish the overlay state during every Alt+Tab transition.
  The native styles are checked at setup; direct interaction remains a Phase 4
  real-session check.
- Other monitor arrangements, Windows DPI scales and PoE2 presentation modes
  were not exercised by this session.
- The tests for rapid Alt+Tab, reopening the same text and interrupted/error ZIP
  packaging remain simulated; this real session completed normally.

## Next checkpoint

**Phase 4 — Local Alpha packaging/runtime UX** is next, not implemented yet.

- Separate normal play startup/stop from the 60-second QC launcher.
- Keep runtime local/offline, foreground guarding and capture exclusion.
- Make setup, runtime status and diagnostics understandable on Windows.
- Test game input, dialogue/menu transitions and Alt+Tab in longer real sessions.
- Keep Python/source-first packaging; build an EXE only after Local Alpha is stable.
- Expand translations later from the pinned fresh sources, without lowering match
  confidence to make untranslated lines display.

The reviewed implementation and QC record are on `fix/phase3-overlay-qc` in
draft PR #1. `main` has not been updated by this QC review.
