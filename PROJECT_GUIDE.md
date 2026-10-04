# POE2 Việt Hóa — Project Guide

## North Star

Xây một engine Việt hóa Path of Exile 2 chạy local trên Windows, bắt đầu bằng Story Dialogue và có thể mở rộng theo module sang Quest, Tutorial, UI, Skill/Passive, Item và Mechanics.

## Nguyên tắc đã chốt

- GitHub `momentum448-glitch/Poe2viethoa` là source of truth.
- Runtime offline, dictionary-first; không dùng AI model để dịch trực tiếp trong lúc chơi.
- Không đọc RAM, không injection/hooking, không tự động gửi input vào game.
- Overlay Normal mode: **che text tiếng Anh và thay bằng tiếng Việt**.
- Khi match không chắc chắn hoặc fuzzy mơ hồ: Normal mode không hiện.
- Git chỉ giữ bản dịch Việt theo source_id; raw English source sync local vào thư mục gitignored.
- Alpha cập nhật dữ liệu bằng release thủ công; updater để sau.
- Python/source-first; đóng EXE sau khi Local Alpha ổn định.
- Không dùng Remote Desktop để khôi phục source.
- Không tái sử dụng dictionary/corpus cũ của dự án trước.

## Kiến trúc

```text
PoE2 screen
  ↓
Foreground guard
  ↓
Capture scheduler
  ↓
Windows OCR + bbox
  ↓
Dialogue context
  ↓
Text stabilizer
  ↓
Exact / fuzzy matcher + ambiguity guard
  ↓
Local runtime translation DB
  ↓
Replacement overlay
```

## Roadmap

### Phase 0 — Signal & architecture validation — PASS
- OCR-first locked.

### Phase 1 — Core capture/context — PASS / LOCKED
- foreground detection;
- screen capture;
- dialogue layout detection;
- frame-change/stability gate;
- Windows OCR + bbox;
- diagnostics/QC packaging.

### Phase 2 — Dialogue matching + fresh translation store — PASS / LOCKED
- fresh-source sync from pinned snapshots;
- deterministic source IDs;
- normalized dedupe;
- exact/fuzzy matcher;
- ambiguity guard;
- JSON Vietnamese entries → local SQLite runtime;
- 60-second real-game QC.

Final real QC `20261004_175216`:
- 54 OCR calls;
- 16 dialogue detections;
- 6 duplicates suppressed;
- 5 High matches;
- 0 errors;
- 60.00 active seconds.

### Phase 3 — Replacement overlay — TECHNICAL + VISUAL QC PASS
- OCR bbox → absolute screen placement;
- mask/cover original English;
- render/wrap Vietnamese;
- click-through/topmost;
- DPI handling;
- foreground hide/show;
- self-capture protection;
- QC proof screenshots.

Current proof uses a transparent Tk/Win32 topmost overlay and `WDA_EXCLUDEFROMCAPTURE` to keep the overlay out of runtime OCR captures.

Real Windows/PoE2 QC `20261004_183317` completed 60 active seconds with 6 exact/High
overlay updates, 5 proof images and no OCR/overlay/runtime errors. Manual image
review passed in normal-right and inventory-left layouts: English covered,
Vietnamese readable, Continue unobstructed. OCR frames retained English while
the overlay was visible; no self-capture loop was observed.

Validation applies to the tested 1920×1080 setup. Direct mouse/keyboard focus
behavior, all foreground transitions and other DPI/presentation modes remain
part of Phase 4 real-session testing. Three unmatched Renly segments are outside
the nine-segment Alpha corpus; they correctly receive no replacement overlay.

### Phase 4 — Local Alpha — PASS / LOCKED
- `RUN_ALPHA.bat` checks local readiness, runs first-time setup when needed and opens the control panel;
- `SETUP_ALPHA.bat` installs dependencies and builds the local DB atomically from pinned sources;
- native Tk panel: Bắt đầu, QC 60 giây, Dừng & tạo ZIP, Mở file kết quả;
- normal play is untimed and records bounded logs without screenshots;
- QC still runs for 60 active foreground seconds and includes proof screenshots;
- one worker process owns OCR/Tk overlay; Stop and foreground hiding remain responsive during pending OCR;
- controller detects worker failures and packages available diagnostics; no game input is automated;
- foreground capture requires the native PoE window class, never a browser/document title alone;
- version/build ID and source fingerprint are recorded in every session;
- passing baseline `0.4.0-alpha.3 / alpha-20261004-03`; Alpha.1 had two clean normal sessions and a completed 60-second technical/visual Renly QC;
- Alpha.2's expanded capture passed visual Una/Renly QC; its larger ROI exposed a chat line falsely anchored by Continue in another column;
- Alpha.3 associates each paragraph with a nearby footer/header before choosing it; the corrected context selection passed Windows QC;
- the user confirmed Continue/movement/Alt+Tab work normally and declared PASS on 2026-10-04 at 21:46 (+07).

Phase 4 is PASS/LOCKED for the tested Windows/1920×1080 setup. The baseline used nine translations.

Latest real QC `20261004_212425_250828`, verified Alpha.3 fingerprint: 456 captures,
53 OCR calls, 24 valid dialogue detections, 15 emitted texts, 9 duplicates,
8 exact/High overlay updates at 100%, 7 readable proof images, no errors,
60.00 active seconds / 61.02 wall seconds. All 24 detected texts match the fresh
source; seven untranslated Una/Renly pages outside the reviewed DB stay hidden.
All 29 rejected frames show topic menus, open-world/chat, waypoint or proclamation,
consistent with the NPC Story Dialogue scope. The prior chat-selection defect
does not recur; Una's short page is selected correctly beside chat. Four Una and
three Renly proofs cover English and leave Continue visible; all eight logged
masks preserve the full translation and cover the complete English OCR box.

The ZIP has zero foreground transitions; direct operation/focus validation comes
from the subsequent user confirmation, not an invented event trace.

### Phase 5 — Translation Factory — CURRENT / FIRST BATCH IMPLEMENTED
- current build `0.5.0-alpha.1 / factory-20261004-01` with 16 reviewed translations;
- `tools.translation_factory`: exact-source selection from QC MISS, batch creation,
  local prompt/review bundle, QA, explicit semantic review, publication and human-QC approval;
- project glossary/style in `translations/glossary.json`; batches bind source/glossary hashes,
  exact source text, context/page metadata and the original catalog record;
- translation memory uses reviewed/approved catalog entries as same-speaker references;
  fuzzy similarity never fills or publishes a draft automatically;
- AI drafting currently happens in chat from the local bundle; no bulk AI API integration;
- QA checks source drift, names, placeholders, numeric literals, duplicates, review digests
  and data changed after review; semantic review remains an explicit authoring step;
- publish preserves existing entries, rejects conflicting catalog revisions/downgrades,
  and writes atomically; runtime builds validate source/VI hashes and preserve an old DB on failure;
- source refresh reuses pinned `tools.source_sync`; meaningful new IDs require new review.

First batch `qc-alpha3-20261004-01`: 3 Una pages (Introduction_4 / Renly) and
4 Renly Fatherhood_2 pages observed in Alpha.3 QC. Seven AI-reviewed pages passed
QA with 0 errors/warnings and compile into the 16-record runtime. All 102 tests
pass; replay of three real QC logs keeps all 22 prior High overlay decisions on
the same IDs, and all seven latest MISS pages now resolve exactly at 100%.

Phase 5 remains CURRENT, with first-batch in-game typography/translation QC pending.
The original nine entries are retained byte-for-byte as JSON records. New seven
entries are `reviewed`, not human `approved`. The next checkpoint is Una
Introduction/Renly and Renly Fatherhood through the existing panel QC workflow.

### Phase 6 — Additional modules
Quest → Tutorial → UI → Skill/Passive → Item/Mechanics.

## Fresh-source rule

Do not recover or import the previous project dictionary.

Raw upstream PoE2 text is reconstructed locally from pinned public snapshots listed in `sources/sources.lock.json`. Raw source/cache/runtime DB directories are gitignored.

Before public distribution of a large translation corpus, re-check current upstream/GGG licensing and distribution constraints.
