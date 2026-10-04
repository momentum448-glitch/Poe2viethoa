# Handoff — POE2 Việt Hóa

## Trạng thái hiện hành

Build **0.5.0-alpha.2 / act1-20261004-01**. Người dùng đã cho thực thi cả chặng
Act 1 và dọn dự án. Triển khai đã hoàn tất; bản mới chờ QC native Windows.
Không hỏi lại để tiếp tục các bước đã được người dùng cho phép.

GitHub `momentum448-glitch/Poe2viethoa` là nguồn chính. Python/source ZIP để người
dùng chạy local và gửi QC 60 giây. Không Remote Desktop; không dùng dictionary
hay corpus 208 dòng của dự án cũ; không AI dịch trực tiếp trong game.

| Phase | Mốc đã giữ |
| --- | --- |
| 1 | PASS/LOCKED QC 163219 |
| 2 | PASS/LOCKED QC 175216 |
| 3 | Technical + visual PASS QC 183317 |
| 4 | PASS/LOCKED Alpha.3 QC 212425; user xác nhận Continue/di chuyển/Alt+Tab 21:46 (+07) |
| 5 | CURRENT; 196 trang đã soát, chưa tự nhận human wording approval |

Baseline QC xác nhận Windows/Python 3.12/1920×1080. Không suy rộng sang cấu hình/DPI
khác. Chi tiết cũ xem [Git checkpoint e4ac909](https://github.com/momentum448-glitch/Poe2viethoa/blob/e4ac909629db04b770be8b17b1aacd17f64698fd/HANDOFF_CURRENT.md).

## Chặng Act 1 vừa triển khai

- 196 trang duy nhất: Una 64, Renly 71, Finn 30, The Hooded One 31.
- Thêm 180, giữ nguyên toàn bộ 16 entry trước. 105 nhóm nguồn gồm biến thể;
  không phải 105 topic menu. 7 lô nội bộ mới, không 7 source ZIP.
- Manifest `translations/manifests/act1_story.json` tham chiếu mọi page ID/order
  gốc, full group hash, source lock, baseline và terms. Corpus dedupe có thể đặt
  một trang dùng chung dưới context đầu tiên; không cắt nhóm theo metadata đó.
- Tất cả mới `reviewed`, reviewer/notes/digest đầy đủ. 8 lô QA 0 lỗi/cảnh báo,
  kể cả lô qc-alpha3 cũ. Không tự tạo `approved` từ việc người dùng gửi ZIP.
- Renly ta/con trong biến thể con nuôi, tôi/bạn cho người lạ; Finn giữ mỉa mai/
  phủ nhận; Una giữ sự chưa chắc; Hooded phân biệt Seed/Beast/Corruption/First Ones.
- Factory `pack`, `coverage`, filter NPC/topic, resume layout ổn định sau publish;
  bundle chứa đủ biến thể/shared pages và style pack. Hash manifest gắn review.
- DB đủ 196, không missing source; build atomic. Không commit raw English/cache/DB.

Nguồn giữ nguyên:
`addohm/poe2-en-cn-dict@28d683c99600eb407b4e014ccaf8247532fb4607`,
`fireMCG/Exiled-Vault@b3dd7457aa4e7f126021b8d8577f38ef205490c7`.
Metadata upstream/GGG terms đã xem ngày 2026-10-04; không tự nhận license/IP game.

## Runtime, hiển thị và dọn

- Glyph guard: so patch chữ sáng/ấm; bỏ nguồn đã đổi trước display, ẩn overlay
  khi page đổi, xác minh lại sau QC proof và restore capture exclusion.
- Padding ngang 18 px. Với Continue đã OCR, dùng chiều cao an toàn trên nút;
  tối đa 22 px; nội dung không vừa thì báo layout error/ẩn, không cắt VI.
- Foreground checks/Stop/self-capture protection còn nguyên. Một worker một
  overlay với runtime lock; phiên lỗi/interruption vẫn đóng gói được kết quả.
- Bỏ QC_PHASE2/3.bat, app/phase2/3_probe.py; test chuyển test_session_runtime.py.
  SOURCE_SYNC và run_tests sang dev/ với cwd sửa; root giữ RUN/SETUP_ALPHA.
- Kết quả mới vào results/. LAST_* ở root và ZIP legacy vẫn restore được.
- Panel có Ghim kết quả này, Dọn kết quả cũ. Cleanup preview trước; giữ ≥5
  mới nhất, LAST, pin và mốc QC. Chặn phiên đang chạy/symlink/ZIP hỏng; apply
  recheck cả selection trước xóa. Diagnostics chỉ xóa nếu exact duplicate ZIP.
- Không giả định đã dọn file trên PC người dùng. Giữ ảnh/log hồi quy khi chưa
  xác minh được ZIP gốc; không xóa bằng chứng duy nhất.

## Xác minh trước phát hành

**128 tests đạt.** 196/196 exact đúng ID; 4 replay giữ 35/35 High cũ.
392 mẫu OCR nhiễu: 387 High đúng, 5 Medium giữ lại, không High sai.
71 cặp ảnh cùng trang không bị glyph guard báo đổi. Guard benchmark Linux
~1 ms/pair, không phải phép đo FPS Windows.

Layout bổ sung dùng DejaVu Sans/Pillow: đủ VI cho 196 trang trong hai vị trí panel;
16–22 px ở envelope nhỏ, 19–22 px ở envelope 173 px. Continue ước lượng từ ảnh.
Không dùng fallback font TK/Xvfb làm bằng chứng Segoe UI native. Cần QC thật mới.

Build fingerprint: **fa03f2605f5367a7a37716c1b77af9d8ade933ecd96c496a453560c63070bbfd**.
Compile/diff checks và CRC source ZIP sạch đã đạt, không chứa cache/raw/runtime.
Fresh ZIP build đủ 196 bằng cache pin; setup core/restart kiểm tra trên Linux với
native checks và pip runner stub, chưa chứng nhận first-run Windows/network.

## QC mới cần đọc và việc tiếp theo

QC baseline `QC_PHASE4_RESULT_20261004_223644_671889.zip`, SHA-256
`7a4ef93ce26863e798ca5c400ca0ea960c5ad816fb1a7a38e2f00f99feed4b44`:
CRC sạch, build 0.5.0-alpha.1/hash e43b03f657bb70dda726a24f2948d31333e7c864e3a9f207576020604ac4bc76,
16 records, 60 giây game/67,89 tổng, 448 capture/53 OCR/32 detections/13 High,
19 duplicates, 12 proofs, 0 MISS/lỗi. Đủ 7 trang lô đầu; hai fuzzy Una Home đúng.
Proof 36 Renly cũ còn glyph mép phải (raw không thấy); nguyên nhân chưa kết luận.
Proof 17 Una Home cũ dùng 14 px. Bản mới đã xử lý code nhưng chưa chứng nhận native.
Một pause/12 transient samples không phải 12 AltTabs; event 33 bị foreground guard
loại trước log, dropped=0. Không chế lại sự kiện thực tế từ chỉ số đếm.

Sau bản chặng này, nhận hai QC 60 giây theo nhóm NPC/topic đã mở. Kiểm tra version,
fingerprint, DB196, CRC/errors, native proof/Continue, trang dài/edgeglyph và guard
stale có gây bỏ quá nhiều trang không. Đọc ảnh ở kích thước gốc; diễn giải log
kèm raw/proof và nguồn pin. Chỉ promote approved khi người dùng xác nhận câu chữ.
Không tạo một release nhỏ cho từng trang MISS; gom topic/nhóm nguồn vào chặng lớn.

Hướng dẫn: [README](README.md), [Guide](PROJECT_GUIDE.md),
[Factory](docs/TRANSLATION_FACTORY.md), [kết quả chặng](docs/ROADMAP_NEXT.md).
