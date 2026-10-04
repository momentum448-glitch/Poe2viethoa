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

### Phase 4 — Local Alpha — CURRENT / IMPLEMENTED, WINDOWS QC PENDING
- `RUN_ALPHA.bat` checks local readiness, runs first-time setup when needed and opens the control panel;
- `SETUP_ALPHA.bat` installs dependencies and builds the local DB atomically from pinned sources;
- native Tk panel: Bắt đầu, QC 60 giây, Dừng & tạo ZIP, Mở file kết quả;
- normal play is untimed and records bounded logs without screenshots;
- QC still runs for 60 active foreground seconds and includes proof screenshots;
- one worker process owns OCR/Tk overlay; Stop and foreground hiding remain responsive during pending OCR;
- controller detects worker failures and packages available diagnostics; no game input is automated;
- foreground capture requires the native PoE window class, never a browser/document title alone;
- version/build ID and source fingerprint are recorded in every session;
- source-first build `0.4.0-alpha.1 / alpha-20261004-01`; Windows launcher, Explorer selection, direct input and real PoE2 QC remain user-machine checks.

Phase 4 is not PASS/LOCKED yet. The nine-segment Alpha corpus remains unchanged.

### Phase 5 — Translation Factory
- fresh-source refresh;
- glossary/canon;
- AI draft;
- automated QA;
- review states;
- translation memory.

### Phase 6 — Additional modules
Quest → Tutorial → UI → Skill/Passive → Item/Mechanics.

## Fresh-source rule

Do not recover or import the previous project dictionary.

Raw upstream PoE2 text is reconstructed locally from pinned public snapshots listed in `sources/sources.lock.json`. Raw source/cache/runtime DB directories are gitignored.

Before public distribution of a large translation corpus, re-check current upstream/GGG licensing and distribution constraints.
