# POE2 Việt Hóa — HANDOFF_CURRENT

**Updated:** 2026-10-04

## Current phase

**Phase 5 — Translation Factory: first milestone implemented; seven new pages awaiting in-game QC**

Phase 1, Phase 2 and Phase 4 are **PASS / LOCKED** on the tested Windows setup.
Phase 3 technical and visual QC passed on session `20261004_183317`.
Current build: **0.5.0-alpha.1 / factory-20261004-01**.

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

The current runtime catalog contains 16 reviewed Vietnamese segments: nine Alpha
baseline pages plus seven from the first Translation Factory batch.

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

## Phase 4 panel QC review and Una capture fix — 2026-10-04

Archive: `QC_PHASE4_RESULT_20261004_202906_038009.zip`, build Alpha.1.
ZIP CRC passed; 53 raw screenshots, 5 overlay proof PNGs and 3 logs/metadata files.
Result: **TECHNICAL_PASS**, 60.00 active game seconds / 64.05 wall seconds.
468 captures, 53 OCR calls, 34 detections, 7 emitted texts, 27 duplicates suppressed,
5 exact/High matches at 100%, 5 overlay updates/proofs, 2 untranslated texts hidden.
0 OCR/overlay/runtime errors or dropped entries; 12 transient foreground losses,
1 pause. Event-derived counters, matcher results and delivered code fingerprint
were independently verified.

All five proof images were visually reviewed:
- events 6, 14, 20, 27: Renly in inventory-left layout;
- event 33: Renly in normal-right layout;
- Vietnamese readable and complete, English entirely covered, Continue unobstructed;
- every logged mask encloses the full English OCR bounding box;
- subsequent raw frames 7, 15, 21, 28, 34 contain English while the overlay is logged
  visible, confirming capture exclusion in these samples without an observed loop.

The two MISS frames 42/43 show real Renly / Clearfell dialogue absent from the
nine-record reviewed Alpha DB. They are exact normalized matches in the fresh
source corpus and correctly remain untranslated. Frame 41 is the rejected topic
menu; frame 49 exposes a separate capture limitation.

**Do not lock Phase 4 from the Renly-only visual pass.** In frame 49, Una's popup
header is around y=625 and its text begins around y=665 in screen coordinates;
the old ROI ends at y=691. The screenshot visibly cuts the paragraph and omits
Continue. Its lower text also falls into the detector's excluded bottom strip,
so it is logged as no dialogue. Frame 50 similarly clips Una's lower topic menu.
This is a capture-coverage defect even though the runtime reports no exceptions.

Fix implemented in **0.4.0-alpha.2 / alpha-20261004-02**:
- `ScreenCapture.default_dialogue_region` expands monitor-relative height from
  25% to 45%; at 1920×1080 the ROI is now (230,421,1190,486), ending at y=907.
- Capture extends through the lower paragraph/Continue area and stays above the
  bottom HUD. Matching thresholds and reviewed translation data are unchanged.
- New regressions exercise lower-popup/Continue coverage, resolution/origin scaling,
  complete lower dialogue recovery and continued rejection of topic menus/bottom chat.
- **All 77 tests passed** on Linux/Python 3.12; compileall and diff whitespace checks passed.
- New code fingerprint: `d7cd08c0cd6c6d1071273159ed9c4b7103f589430dfb64e7a473bbf8983233d8`.

The missing pixels below the original PNG cannot be recovered locally. The
expanded ROI was tested with simulated geometry/OCR; actual Windows OCR/overlay
and performance with the larger capture still require the next user QC.

Next checkpoint (supersedes previous QC requests):
1. Download the corrected Alpha.2 build, extract a fresh folder and run `RUN_ALPHA.bat`.
2. Select **QC 60 giây** and exercise **Una → Home / Clearfell**, then one known
   Renly Introduction / The Miller segment to check the existing overlay layout.
3. Send `QC_PHASE4_RESULT_*.zip`; metadata must identify Alpha.2, and screenshots
   must contain the complete Una paragraph and Continue. Confirm game input works.

Phase 4 remains CURRENT / FIX IMPLEMENTED / WINDOWS QC PENDING. The Renly visual
checkpoint is passed on Alpha.1; full Alpha locking and translation expansion
wait for validation of the observed Una crop fix.

## Phase 4 Alpha.2 review and local anchor fix — 2026-10-04

Archive: `QC_PHASE4_RESULT_20261004_205252_628160.zip` (59,850,354 bytes; CRC passed).
SHA-256: `2e310472b94ea3ea8243648734ffc9be502a3fb7cf2d56140bd71217644f8306`.
Metadata identifies Alpha.2 with the expected code fingerprint, Windows/Python
3.12.10, native `POEWindowClass`, 1920×1080 and ROI (230,421,1190,486).
52 raw screenshots, 7 overlay proofs, 3 logs/metadata files; 9 reviewed DB records.
Automatic result **TECHNICAL_PASS**, completed after 60 active seconds / 61.08 wall seconds.

- 454 captures, 52 OCR calls, 38 reported detections, 14 emitted texts, 24 duplicates;
- 9 High matches/overlay updates: 7 exact at 100%, 2 correct fuzzy matches at
  95.90% and 95.96% despite missing OCR text inside the paragraph;
- 2 Medium results correctly hidden, 3 unmatched texts, 3 overlay clears;
- 0 OCR/overlay/runtime errors, foreground losses/pauses or dropped log entries.

Independently recounted event-derived counters, replayed all 14 emitted matches
against the reviewed DB, and checked all 9 English-mask rectangles/full wrapped
Vietnamese strings. All seven proofs were visually reviewed: Una at events
7/24/31/37 and Renly at 49/51/52. Vietnamese is readable and complete, English is
covered, and Continue is unobstructed. Una appears in both normal-right and
inventory-left layouts; the expanded ROI contains the full lower popup/footer.
Raw frames 8/25/50 retain English while the overlay is logged visible, supporting
capture exclusion in these samples. The Una capture fix has passed this checkpoint.

Two real untranslated Una texts are exact normalized fresh-source matches outside
the nine-record DB: event 4 / Introduction_4 (`dlg_npctextaudio_73589ca681a9d260d834`)
and event 17 / Renly (`dlg_npctextaudio_e8a97f822abbe36370a9`). Event 20 is different:
a global-chat trade message at ROI x=7/y=316 was selected over Una's short story
paragraph at the right. The detector used a global Continue flag, so Una's footer
incorrectly anchored chat in another column. Low match score 31.67 prevented an
overlay, but this is a real context-selection defect; do not lock Phase 4 yet.

Fix in **0.4.0-alpha.3 / alpha-20261004-03**:
- associate Continue with each paragraph using horizontal overlap and a bounded
  gap below the paragraph; reject a footer above, far below or in another column;
- select an anchored paragraph before an unanchored high-scoring text cluster;
- associate speaker labels locally; permit a lower Una header when its paragraph
  has a local Continue, retaining the upper-third guard for speaker-only fallback;
- five new regressions and a strengthened Una speaker assertion; the observed
  chat case and four other assertions failed on Alpha.2 before the fix;
- **all 82 tests passed** on Linux/Python 3.12; compileall and diff checks passed;
- code fingerprint: `660079cb57bcbfa72906fc0bf613b50650dc43c57b55602aede601f35387e1da`.

The observed event is reproduced using its logged chat text/box and representative
header/paragraph/footer geometry from the PNG. The ZIP does not preserve all raw
OCR line boxes; no claim is made that its entire Windows OCR result was replayed.
Matching thresholds, nine translations and expanded capture geometry are unchanged.

Next checkpoint (supersedes earlier download/QC instructions): download Alpha.3,
extract a fresh folder, run `RUN_ALPHA.bat` and choose **QC 60 giây**. Exercise Una
Home / Clearfell and Renly Introduction / The Miller with Inventory open/closed;
keep existing chat visible if present, without sending messages. Hold each page
3–4 seconds and try Alt+Tab while Vietnamese is visible. Send `QC_PHASE4_RESULT_*.zip`
and confirm mouse/keyboard input still works normally.

Phase 4 remains CURRENT / CONTEXT FIX IMPLEMENTED / WINDOWS QC PENDING. Una and
Renly visual checkpoints passed; the new local anchor selection, direct interaction
and foreground-transition behavior still need the next real Windows session.

## Phase 4 Alpha.3 Windows QC — technical and visual PASS — 2026-10-04

Archive: `QC_PHASE4_RESULT_20261004_212425_250828.zip` (59,910,561 bytes; CRC passed).
SHA-256: `8f75ef124346101e2bc4b9b2a89d3013187194bdbfc4ae75d7a937d76941d8a5`.
Metadata confirms **0.4.0-alpha.3 / alpha-20261004-03**, fingerprint
`660079cb57bcbfa72906fc0bf613b50650dc43c57b55602aede601f35387e1da`,
Windows/Python 3.12.10, native `POEWindowClass`, 1920×1080, ROI (230,421,1190,486)
and the unchanged nine-record DB. Pack: 53 raw PNGs, 7 proofs, 3 logs/metadata files.
Result **TECHNICAL_PASS**, completed after 60 active seconds / 61.02 wall seconds.

- 456 captures, 53 OCR calls, 24 dialogue detections, 15 emitted texts, 9 duplicates;
- 8 High matches/overlay updates, all exact at 100%; 0 Medium results;
- 7 unmatched real dialogue pages correctly hidden; 4 overlay clears;
- 0 OCR/overlay/runtime errors, dropped log entries, foreground losses or pauses;
- 5 normal-right and 19 inventory-left detections; all 15 Una detections identify Una.

Independent review verified the code fingerprint, event-derived counters, all
15 matcher results and all 8 mask rectangles/full wrapped Vietnamese strings.
All 24 detected texts are exact normalized matches in the pinned fresh corpus.
All seven proofs were visually inspected: Una at 9/22/24/26, Renly at 32/34/35.
English is fully covered, Vietnamese is readable/complete and Continue remains
unobstructed. Raw frames 10 and 23 visibly retain English while the overlay is
logged visible, supporting capture exclusion without an observed self-OCR loop.
Event 14 correctly redisplays the same Una translation after Inventory changes
the layout; this extra update shares a source ID with proof 9.

All 29 rejected raw frames were reviewed in contact sheets. They show topic
menus, open-world/chat, waypoint or proclamation rather than NPC story paragraphs.
The previous chat false positive does not recur. In event 19 the short Una page
"In many ways, he reminds me of my father..." is correctly selected beside chat;
it matches the fresh source and stays hidden because no reviewed Vietnamese
record exists. This validates the context fix in the recorded Windows samples,
without claiming every possible future chat/layout case has been tested.

The seven MISS pages are outside the reviewed DB, all exact fresh-source matches:
- Una / Introduction_4: `dlg_npctextaudio_73589ca681a9d260d834`;
- Una / Renly: `dlg_npctextaudio_e8a97f822abbe36370a9`,
  `dlg_npctextaudio_aa67074040f344406e17`;
- Renly / Fatherhood_2: `dlg_npctextaudio_5e32138d2437af6705d0`,
  `dlg_npctextaudio_0c44edf04fad4428bdb3`, `dlg_npctextaudio_a43ba9fa1fbebc488dad`,
  `dlg_npctextaudio_675b99e134d0178394ad`.
No new translations or matching-threshold changes are justified by these MISS pages.

No code fix or new build is required by this review. Keep Alpha.3. Technical and
visual QC are PASS for the recorded Windows/1920×1080 setup. **Phase 4 is not yet
fully PASS/LOCKED:** the pack records no foreground transitions and cannot establish
direct mouse/keyboard/focus behavior. The Alpha.3 session does not prove Alt+Tab
hide/restore merely because earlier builds exercised that path.

Next checkpoint, superseding the previous 60-second download/QC request:
1. Ask whether Continue, movement and Alt+Tab out/back worked normally while
   Vietnamese was visible. This is an operation-result confirmation, not publish approval.
2. If not tried, use current Alpha.3 normal Start with a reviewed Una/Renly page;
   check Continue/movement, overlay hiding outside PoE2 and restoration on return.
   The user can report the result directly; request a result ZIP if a problem occurs.
3. Once the operation result is confirmed, mark Phase 4 PASS/LOCKED and start
   Phase 5 Translation Factory from pinned source IDs, review states and glossary.

This documentation checkpoint leaves the runtime fingerprint and nine translations unchanged.

## Phase 4 closure and Phase 5 first milestone — 2026-10-04

At 21:46 (+07), the user confirmed Continue/movement/Alt+Tab work normally,
declared PASS and asked to continue. This closes the pending operation-result
checkpoint. **Phase 4 is PASS/LOCKED** for the tested Windows/1920×1080 setup,
using Alpha.3 technical/visual evidence plus the user's direct confirmation.
The confirmation is reported human evidence, not an invented foreground event log.

Implemented Translation Factory first milestone:
- `tools/translation_factory.py`: prepare from explicit IDs or exact QC MISS,
  source/context/TM bundle, QA, explicit semantic review, publish and user approval;
- `translations/glossary.json`: project dialogue voice and preserved proper names;
- `translations/batches/qc-alpha3-20261004-01.json`: seven source-bound Vietnamese
  drafts, per-page drafting decisions, review notes/digests and pinned source/glossary;
- `docs/TRANSLATION_FACTORY.md`: repeatable authoring/publication/revision workflow;
- `app/translation_store.py`: rejects malformed/duplicate/status-invalid data and
  changed source/VI hashes on factory entries; nine legacy records are retained intact;
- `tools/build_translation_db.py`: temporary DB build and atomic replacement,
  preserving an old DB if validation/build fails;
- build fingerprint now includes glossary and batch JSON as well as code/catalog/pins.

The local bundle supplies fresh English source pages, neighboring pages from the
same upstream record, project style and same-speaker reviewed translation memory.
AI drafting/review currently runs in chat; bulk AI API integration is not implemented.
Automatic QA checks structural rules, not complete semantic accuracy. Reviewed
pages may run in Alpha; approved records require the user's QC report and are
protected from downgrade. Batch edits after review invalidate the recorded digest.
Pinned corpus/glossary changes require new batch preparation/review rather than
automatic fuzzy reuse. Factory operators write the catalog sequentially.

First batch: **7 AI-reviewed pages**, selected from the Alpha.3 exact-source MISS
events 5/17/19/40/41/42/43. Three Una pages: Introduction_4 and both Renly pages;
four Renly Fatherhood_2 pages. The translations preserve the custody actor,
Karui name, uncertainty about the child's origin, paternal worry and Una's tone.
Draft notes record those choices. They are `reviewed`, awaiting human QC/approval.

Validation completed:
- **102 tests passed** on Linux/Python 3.12 (20 factory regressions plus 82 baseline tests);
- CLI prepare/bundle/QA/review/publish exercised against the actual 25,062-page
  pinned corpus; seven drafts passed QA with 0 errors and 0 warnings;
- runtime build: 16 compiled/displayable records, 0 missing source, 0 skipped empty;
- all nine baseline translation JSON records remain identical;
- replay of Alpha.1/2/3 QC keeps all 22 prior High overlay decisions on the same IDs;
- in latest Alpha.3 QC, all 15 emitted texts resolve exactly at 100%, including
  all seven former MISS pages; the old Alpha.2 trade chat remains Low/unmatched;
- compileall and Git diff checks pass; no raw corpus/report/runtime files are committed.

Current build **0.5.0-alpha.1 / factory-20261004-01**; source fingerprint
`e43b03f657bb70dda726a24f2948d31333e7c864e3a9f207576020604ac4bc76`.
Actual Windows rendering of
the seven new translations has not been observed yet; do not claim Phase 5 PASS
from matcher replay or Linux tests. OCR/capture/overlay/panel logic remains at the
passing Phase 4 implementation; this release adds factory/data/build validation.

Next checkpoint: download the new source bundle, extract a fresh folder, run
`RUN_ALPHA.bat`, select **QC 60 giây**. Exercise **Una → Introduction / Renly** and
**Renly → Fatherhood**, each page held 3–4 seconds; change Inventory layout and
check one existing Renly Introduction page. Send `QC_PHASE4_RESULT_*.zip` and
language/readability feedback. Expect version `0.5.0-alpha.1` and 16 runtime records.
After the user's new-page QC passes, approve/publish this batch using the factory
workflow, then prepare the next batch from exact MISS pages observed during play.
