# POE2 Việt Hóa — HANDOFF_CURRENT

**Updated:** 2026-10-04

## Current phase

**Phase 4 — Local Alpha: normal Windows sessions clean, 60-second visual QC pending**

Phase 1 and Phase 2 are **PASS / LOCKED**.
Phase 3 technical and visual QC passed on session `20261004_183317`.
Current build: **0.4.0-alpha.1 / alpha-20261004-01**.

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
- At pre-QC review time, native integration/readability remained unverified.
  The subsequent real-game QC below supplied that evidence on the tested setup.
  Automated native-boundary tests still use mocks.

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

The user authorized continuing after Phase 3 QC. PR #1 was merged into `main`
at `f98e354ff868e4d2bbd073a37507c512b9a28efb`.

## Phase 4 implementation — ready for Windows QC

- `app/session_runtime.py` is the shared capture/context/matching/overlay engine;
  `app/phase3_probe.py` remains a compatible standalone QC CLI.
- `app/alpha_app.py` provides the native Tk control panel; `app/alpha_controller.py`
  spawns one overlay worker, polls status without blocking the panel, requests
  graceful Stop and recovers diagnostics on a worker crash/forced stop.
- Normal play is untimed. Stopping creates `ALPHA_RESULT_*.zip`, without images.
  Event/error logs are bounded to 4/1 MiB; dropped event entries are counted.
- Panel QC runs 60 active PoE2 foreground seconds and creates
  `QC_PHASE4_RESULT_*.zip` with raw OCR/proof images. Stopping early is INTERRUPTED.
- Runtime remains offline and High-confidence-only. No hooks, memory reads,
  game-file edits or automated mouse/keyboard input were added.
- Foreground guarding now requires `POEWindowClass` / `POE2WindowClass`.
  A browser, console or document titled Path of Exile 2 cannot qualify for capture.
- Pending OCR is polled for Stop/foreground loss and times out after 8 seconds;
  stale OCR from a foreground loss is discarded even if the game returns.
- Windows OCR bitmap/writer resources are explicitly closed on success/failure.
- `app/runtime_lock.py` prevents overlapping workers in the same installation;
  the OS releases its lock on process exit. A lingering lock file is not a stale lock.
- `RUN_ALPHA.bat` does a network-free local readiness check. First run uses
  `SETUP_ALPHA.bat` / `tools/alpha_setup.py` to install dependencies, sync the pinned
  source if needed and replace the runtime DB only after a successful build.
- Setup stamps track Python, requirements, source lock and translations. Normal
  startup performs no downloads when local readiness passes.
- Closing the panel requests Stop and waits for resource cleanup. Existing
  result pointers are restored on the next launch; new sessions use unique names.
- Every diagnostic pack records version, build ID and SHA-256 of actual code/data
  files, including GitHub ZIP downloads with no `.git` directory.

Validation:
- All 73 automated tests passed on Linux/Python 3.12. They cover normal/paused Stop, pending OCR cancellation/timeout,
  foreground loss during OCR, normal/QC result labels, bounded logs, crash recovery,
  worker restart, real spawned-worker failure return, lock release, offline readiness,
  atomic DB failure preservation and browser-title rejection, plus previous tests.
- Reconstructed the pinned fresh source locally: 25,062 corpus segments; built
  the unchanged 9 reviewed Vietnamese runtime records. Linux validation mocks
  Windows package/platform checks; native Windows dependency installation is pending.
- Native Tk control-panel start/stop/QC/status/restart behavior was exercised
  under Linux Xvfb with a simulated worker. This does not validate Windows styling,
  batch launch, Explorer or the actual OCR/overlay worker in PoE2.
- No Remote Desktop and no old project dictionary/corpus were used.

Next user checkpoint:
1. Download/extract the new source ZIP and open `RUN_ALPHA.bat`.
2. Try normal Bắt đầu, Alt+Tab, Dừng & tạo ZIP, and start again. Check that game
   mouse/keyboard input remains unaffected and no stale overlay is retained.
3. Run panel QC 60 giây on the Alpha topics, including normal/inventory layouts
   and a foreground switch while Vietnamese is visible.
4. Use Mở file kết quả and send `QC_PHASE4_RESULT_*.zip` back to the project chat.

Phase 4 remains CURRENT, not PASS/LOCKED, until this Windows/PoE2 checkpoint.
Python/source-first packaging remains the plan; build an EXE after Local Alpha
is stable. Translation expansion is a later checkpoint, using the pinned fresh
sources without lowering confidence to display untranslated lines.

## Phase 4 normal-session review — 2026-10-04 20:10 (+07)

Archive: `ALPHA_RESULT_20261004_200920_160211.zip`.
Delivered code: `3e20515c6f3b79fc3688c6175f2cc1cabeeeeb04` (PR #2 merged).
Build: `0.4.0-alpha.1 / alpha-20261004-01`.
Code fingerprint: `a85cf75e0482540c5f6856382d89a3149d1c61d79c1670f72293bee9966e8b9f`,
matching the delivered/local code. Windows Python 3.12.10, 1920×1080;
actual foreground class `POEWindowClass`, title Path of Exile 2.

Technical result: normal session ended cleanly as **STOPPED**, with no reported
OCR, overlay, runtime or cleanup errors. Archive CRC passed.

- 38.27 active game seconds / 42.16 wall seconds; untimed normal mode.
- 303 captures, 34 OCR calls, 26 dialogue detections, 13 emitted texts.
- 6 exact/High matches at 100%, 6 overlay updates across 5 unique reviewed IDs.
- 13 duplicates suppressed; 7 untranslated texts correctly left without overlay.
- 0 errors, 0 dropped log entries; 12 transient foreground losses / 1 pause.
- Normal-right 14 detections; inventory-left 12. Events 17→19 redisplayed the
  same translated line after the layout changed, rather than suppressing it.
- Three ZIP entries only: metadata, summary and event log; no screenshots/proofs,
  as intended for lightweight normal play. Compressed pack size 5,360 bytes.

Independent review recounted event-derived totals and matched the summary.
All six translations match the local reviewed DB and normalized source exactly.
All six logged masks contain the complete English OCR rectangle, and all six
wrapped Vietnamese strings preserve the full translation. Font sizes were 18–20 px.
Subsequent duplicate events still OCR English while the overlay is logged visible,
with no observed self-capture in the recorded text. This does not replace visual QC.

The seven MISS texts are exact normalized matches in the pinned fresh corpus,
all outside the nine-record Vietnamese Alpha DB:
- Renly / Clearfell: `d36d07b4b366ffa08c4d`, `6061aa2dd44da67d0163`, `7339cdf9c4a48f93f01f`;
- Renly / Ogham: `fc70663467362963c971`;
- Renly / Fatherhood_2: `5e32138d2437af6705d0`, `0c44edf04fad4428bdb3`, `a43ba9fa1fbebc488dad`.
IDs above are the suffixes after `dlg_npctextaudio_`. They are real dialogue,
not falsely detected UI. Do not lower matching thresholds to display them.

This establishes a clean real Windows normal-runtime/Stop/ZIP checkpoint.
The log-only archive cannot establish readable rendering, actual Continue-button
clearance, direct input/focus, restart behavior or every foreground transition.
No code change or new download is required by this review.

Next user checkpoint (supersedes the pre-release download steps above):
1. Reuse the current build; choose panel **QC 60 giây** and open Renly Introduction /
   The Miller. Exercise normal/inventory layouts and Alt+Tab while Vietnamese is visible.
2. After 60 active seconds, use **Mở file kết quả** and send `QC_PHASE4_RESULT_*.zip`.
3. Check a second normal Start/Stop and that mouse/keyboard input still works normally.

Phase 4 remains CURRENT; full PASS/LOCKED awaits the Alpha visual/interaction QC.

## Phase 4 second normal-session review — 2026-10-04 20:23 (+07)

Archive: `ALPHA_RESULT_20261004_202018_804304.zip` (8,307 bytes; CRC passed).
Same build/code fingerprint as the first Alpha session. The second real Windows
normal run ended cleanly as **STOPPED**, without reported errors.

- 181.56 active seconds / 195.51 wall seconds; 1,427 captures, 165 OCR calls.
- 29 dialogue detections: 19 normal-right, 10 inventory-left.
- 15 emitted texts, 14 duplicates suppressed, 10 High matches/overlay updates.
- 9 exact matches at 100%; one correct fuzzy match at 99.11% recovered OCR
  `infor` instead of `in for` in Renly / The Miller (event 74).
- 5 untranslated texts correctly hidden: two Renly / Fatherhood_2, three Renly /
  Clearfell, all exact normalized matches in the fresh corpus outside the Alpha DB.
- 0 OCR/overlay/runtime errors or dropped entries; 35 transient foreground losses,
  2 pauses; all 10 logged masks cover English completely and retain all Vietnamese text.

Independently recounted summary totals, replayed every emitted match against the
local matcher/DB, and verified the code fingerprint and logged geometry/text.
This also confirms normal mode continues beyond 60 seconds. It does not prove a
restart within the same panel process, direct interaction or visual appearance.

The pack is **normal mode**, not panel QC: `mode=alpha`, `duration_seconds=null`,
`screenshots_enabled=false`; three log/metadata/summary entries and zero proof images.
Do not mark Phase 4 visual QC PASS from this archive or infer which button the user
pressed. They may have sent a normal pack instead of an existing QC pack.

Next user checkpoint: if QC was already run, find/send `QC_PHASE4_RESULT_*.zip`
in the same extracted project folder. Otherwise reopen `RUN_ALPHA.bat` and choose
**QC 60 giây**, the middle button between Bắt đầu and Dừng & tạo ZIP. Wait for QC
hoàn tất after 60 active game seconds, then send its result ZIP. Keep the current
build; no engine change or new download is required by this review.
