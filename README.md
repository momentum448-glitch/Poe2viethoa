# POE2 Việt Hóa

Local-first Vietnamese localization engine for Path of Exile 2.

## Current phase

**Phase 5 — Translation Factory: seven new pages passed technical/visual QC; larger milestone planned**

Phase 1, Phase 2 and Phase 4 are **PASS / LOCKED** on the tested Windows setup.
Phase 3 technical and visual QC passed on session `20261004_183317`.
Current build: **0.5.0-alpha.1 / factory-20261004-01**.

QC Alpha.3 `20261004_212425_250828`: 60 giây trong game, 8 lần hiện bản dịch
khớp 100%, 0 lỗi OCR/overlay/runtime. Cả 7 ảnh Una/Renly đều rõ chữ, che đủ
tiếng Anh và không đè Continue. Cả 24 lần nhận diện đều là lời thoại thật;
không còn nhận nhầm chat trong phiên này. Bảy câu chưa dịch nằm ngoài bộ Alpha.
Kỹ thuật và hình ảnh đã đạt trên cấu hình Windows/1920×1080 được thử. Người dùng
xác nhận Continue/di chuyển/Alt+Tab bình thường và PASS lúc 21:46 ngày 2026-10-04.
Phase 4 đã được chốt; các cấu hình/DPI khác chưa nằm trong phạm vi xác nhận này.

Lô Factory đầu tiên thêm 7 đoạn Una/Renly từ các MISS đã xác minh, đưa bộ dịch
lên **16 đoạn**. Lô đã được AI soát nghĩa và qua QA cấu trúc: 0 lỗi, 0 cảnh báo.
Công cụ tạo nháp, glossary, gói nguồn/context, bộ nhớ bản dịch, duyệt và đưa vào
catalog đã có; **102 kiểm thử đạt**. QC `20261004_223644_671889` đã xác minh đủ
7 đoạn mới trong game: 13 lượt High (11 exact, 2 fuzzy đúng trang), 0 MISS,
0 lỗi OCR/overlay/runtime. Bảy đoạn mới rõ chữ, che đủ tiếng Anh và để trống Continue.
Một ảnh Renly cũ còn vệt ký tự ở mép mặt nạ; đoạn Una Home dài dùng chữ 14 px.
Hai điểm này nằm trong chặng tiếp theo cùng gói Story Dialogue khoảng 180–220 trang.
Xem [kế hoạch chặng lớn và dọn dẹp](docs/ROADMAP_NEXT.md). Lượt này chỉ cập nhật
kết quả QC/kế hoạch; code, 16 bản dịch và fingerprint giữ nguyên.

## Chạy Local Alpha

1. Giải nén bản mới vào một thư mục, rồi mở **RUN_ALPHA.bat**.
2. Lần đầu tool tự thiết lập thư viện và dữ liệu từ nguồn đã pin; bước này cần mạng.
   Python 3.10+ cần được cài sẵn, bản đã QC dùng Python 3.12. Các lần chạy sau dùng dữ liệu offline.
3. Chọn **Bắt đầu** để chơi. Cửa sổ điều khiển thu nhỏ; chuyển sang PoE2.
   Chế độ này chạy đến khi bấm Dừng, không tự kết thúc sau 60 giây.
4. Alt+Tab quay lại bảng điều khiển, bấm **Dừng & tạo ZIP** để dừng và xuất log.
   **Mở file kết quả** mở Explorer và chọn file cần gửi.

Chế độ chơi tạo `ALPHA_RESULT_*.zip` với log nhẹ, không lưu ảnh. Log sự kiện
được giới hạn 4 MiB và log lỗi 1 MiB mỗi phiên; tổng bộ đếm vẫn tiếp tục cập nhật.
Không tự xóa các kết quả cũ. Đóng cửa sổ điều khiển cũng yêu cầu dừng phiên;
kết quả lần trước được khôi phục khi mở lại bảng điều khiển.

Để QC bản Alpha, chọn **QC 60 giây** trong bảng điều khiển, rồi chuyển sang game.
Timer chỉ tính thời gian PoE2 ở foreground. QC thu ảnh vùng hội thoại, tạo
**QC_PHASE4_RESULT_*.zip** và hiện tên file sau khi hoàn tất. Gửi ZIP đó lại trong chat.
Nếu bấm Dừng trước đủ 60 giây, kết quả là `INTERRUPTED`, không phải PASS.

QC lô mới: thử **Una → Introduction / Renly** và **Renly → Fatherhood**.
Giữ mỗi trang 3–4 giây; thử mở/đóng Inventory, rồi xem lại một trang Renly
Introduction đã dịch trước đó. Gửi `QC_PHASE4_RESULT_*.zip` như quy trình hiện tại.

Bản mới có **16 đoạn hội thoại đã dịch**: Renly Introduction / The Miller /
Fatherhood, Una Introduction / Home / Clearfell / Renly. Các câu ngoài bộ này
giữ nguyên tiếng Anh. Factory đang ở lô đầu, chưa phải toàn bộ hội thoại PoE2.
Nếu cần thiết lập lại, chạy **SETUP_ALPHA.bat**. Nếu không mở được bảng điều khiển,
gửi `ALPHA_STARTUP_ERROR.txt` nếu file này được tạo.

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

Quy trình soạn/duyệt lô dịch nằm trong [docs/TRANSLATION_FACTORY.md](docs/TRANSLATION_FACTORY.md).
AI soạn dữ liệu trong giai đoạn chuẩn bị; khi chơi, runtime dùng SQLite offline.

## Legacy Phase 3 QC

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

The pre-QC code review fixed native window selection, 64-bit HWND handling,
English-mask coverage, text overflow, quick Alt+Tab/reopen recovery, and ZIP
creation after runtime failure or interruption.

Result labels:
- `TECHNICAL_PASS`: the automated checks completed; real-game visual QC is still required.
- `NEEDS_REVIEW`: the session completed but one or more technical checks did not pass.
- `ERROR` / `INTERRUPTED`: the session failed or stopped early; send the partial result ZIP.

Phase 3 needs Windows 10 build 19041 or newer for capture exclusion.

## Phase 3 QC result

Real Windows/PoE2 session `20261004_183317`: **technical and visual QC PASS**.

- 60.00 active seconds; 76.50 seconds wall time;
- 467 captures, 53 OCR calls, 25 dialogue detections;
- 6 exact/High matches and overlay updates, 5 unique overlay proof images;
- 16 duplicates suppressed; 3 untranslated dialogue segments correctly hidden;
- 0 OCR, overlay or runtime errors.

Manual review of all five proof images confirms readable Vietnamese, complete
English coverage and an unobstructed Continue button in normal-right and
inventory-left layouts. Subsequent OCR screenshots still contain English while
the overlay is marked visible, with no observed self-capture loop. All six logged
masks cover their complete English bounding boxes.

This validates the tested 1920×1080 setup. The pack does not directly establish
mouse/keyboard focus behavior, every Alt+Tab transition, or other DPI/presentation
modes; retain those checks in Phase 4 real-session testing. The three MISS segments
are real Renly dialogue outside the nine-segment Alpha corpus.

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
