# Chặng Act 1 Story Dialogue và dọn dự án

Ngày: 2026-10-04. Người dùng đã cho thực thi trọn chặng.
**Đã triển khai Act 1: 0.5.0-alpha.2 / act1-20261004-01.**
Runtime hiện hành **0.5.0-alpha.3 / popup-20261005-01** sửa vị trí NPC;
[báo cáo hai QC 2026-10-05](QC_POPUP_20261005.md). Các số liệu dưới đây là mốc
chặng Alpha.2; native proofs mới xác nhận Home 19 px, bản sửa Alpha.3 chờ QC.
Mục tiêu 180–220 trang đã đạt bằng 196 trang có nguồn; không tăng bằng bark/vendor.

## Kết quả

| Công việc | Kết quả |
| --- | --- |
| Chốt nguồn | 196 source ID duy nhất, 105 nhóm nguồn với đầy đủ Continue và trang dùng chung |
| Factory | Lô theo manifest/NPC/topic, resume ổn định sau publish, coverage và bundle đủ biến thể |
| Dịch/soát | Thêm 180 trang trong 7 lô; giữ nguyên 16 trang baseline; 8 lô QA 0 lỗi/cảnh báo |
| Runtime | DB 196 records, exact đúng cả 196; bỏ kết quả stale và kiểm tra nguồn sau proof |
| Hiển thị | Padding ngang 18 px, dùng khoảng trống trên Continue, tối đa 22 px; không cắt nội dung để tăng font |
| Hồi quy | 128 tests; 35 High cũ đúng ID, 392 mẫu OCR nhiễu không High sai, 71 cặp cùng trang ổn định |
| Dọn | Bỏ launcher/probe cũ, giữ test shared runtime, dev scripts riêng, docs rút gọn, results/pin/preview cleanup |
| Phát hành | Một source ZIP cố định cho cả chặng; không phát hành từng lô nội bộ |

| NPC | Tổng | Thêm mới |
| --- | ---: | ---: |
| Una | 64 | 57 |
| Renly | 71 | 62 |
| Finn | 30 | 30 |
| The Hooded One | 31 | 31 |
| Tổng | 196 | 180 |

105 nhóm là các source group/biến thể, không phải 105 topic menu khác nhau.
5528 từ nguồn và 6319 từ VI đếm trên 196 trang duy nhất; câu VI dài nhất 287 ký tự.
Manifest `translations/manifests/act1_story.json` giữ page ID/order/full-group hash,
source lock, baseline và thuật ngữ. Những trang lặp qua biến thể được tham chiếu
ở mọi nhóm; corpus dedupe không được dùng để cắt mất trang của nhóm gốc.

## Bằng chứng và giới hạn

Baseline `QC_PHASE4_RESULT_20261004_223644_671889.zip`, SHA-256
`7a4ef93ce26863e798ca5c400ca0ea960c5ad816fb1a7a38e2f00f99feed4b44`:
60 giây game / 67,89 tổng, 448 captures, 53 OCR, 32 detections, 13 High,
19 duplicates, 12 proofs, không MISS/lỗi. Bảy trang lô đầu đủ chữ, che English,
chừa Continue. Hai fuzzy Una Home đúng trang khi chat che dòng cuối OCR.
Một pause và 12 mẫu transient-loss không phải 12 lần Alt+Tab. Event 33 bị guard
loại khi foreground đổi; dropped=0.

Proof 36 Renly cũ có glyph ở mép; raw tương ứng không có glyph đó. Nguyên nhân
chưa được chứng minh. Bản mới nới vùng che có giới hạn ROI/Continue, so glyph
trước khi hiển thị, ẩn khi nguồn đổi và loại proof đã lỗi thời. Các kiểm thử xử lý
được page change trong khi OCR/proof đang chờ; chưa có proof Windows của bản mới.

Una Home cũ dùng 14 px. Bản mới tận dụng chiều cao đã đo phía trên Continue.
Audit DejaVu Sans/Pillow trên Linux giữ đủ cả 196 VI: 19–22 px trong envelope
173 px, 16–22 px trong hai envelope nhỏ hơn lấy theo vị trí ảnh QC. Continue của
kiểm tra bổ sung được ước lượng từ ảnh; không coi đây là đo font Segoe UI/Windows.
TK/Xvfb chỉ kiểm tra cấu trúc panel bằng fallback font; không chứng nhận glyph native.

Replay matcher trên 4 log QC giữ đúng cả 35 High cũ. Log Alpha.2 có chat từng bị
context nhận sai: chat vẫn Low, đoạn trộn/thiếu mơ hồ vẫn bị giữ lại; detector hiện
hành có tests cho footer khác cột. Đây là replay dữ liệu, không phải chạy game mới.

Toàn bộ bản mới là `reviewed` sau soát nghĩa AI/author; chưa tự gắn `approved`.
QC native sau chặng: hai phiên 60 giây, Una/Renly và Finn/Hooded theo topic đang mở;
ưu tiên Home dài, Introduction cũ, Inventory và Alt+Tab. Có thể chơi thường thêm
10–15 phút để tìm MISS. Phase 5 chỉ khóa sau bằng chứng phù hợp và xác nhận người dùng.

## Dọn đã thực hiện và cách giữ bằng chứng

| Nhóm | Trạng thái hiện hành |
| --- | --- |
| QC_PHASE2/3.bat và phase2/3_probe.py | Bỏ; shared runtime/panel thay thế, lịch sử giữ trong Git |
| test_phase3_probe.py | Đổi thành test_session_runtime.py, giữ toàn bộ lifecycle tests |
| SOURCE_SYNC/run_tests.bat | Chuyển vào dev/, sửa cwd và reference |
| RUN_ALPHA/SETUP_ALPHA.bat | Giữ root |
| README/Guide/Handoff | Chỉ hướng dẫn và trạng thái hiện hành; handoff dưới 200 dòng |
| ADR/glossary/batches/manifest/source lock | Giữ vì còn là dependency/provenance |
| ZIP mới | results/; con trỏ cũ ở root vẫn đọc được |
| ZIP/chẩn đoán cũ | Preview thủ công, giữ ≥5 mới nhất + LAST + pin + mốc PASS |
| Source cache/DB/dependencies | Giữ, không xóa dữ liệu chạy offline |

Cleanup chỉ xét ZIP theo tên kết quả trong root/results; chặn symlink và ZIP hỏng.
Thư mục diagnostics chỉ xóa khi mọi file khớp bản đã xác minh trong ZIP; file
độc nhất không bị đụng. Apply recheck toàn bộ selection và giữ runtime lock trước
khi xóa. Nếu pointer/pin/file đổi sau preview, kế hoạch bị từ chối và cần xem lại.
Không tự dọn lúc khởi động, không xóa file ngoài bản cài và không giả định đã dọn
thư mục trên máy Windows của người dùng.

Các ảnh/log QA đang dùng cho hồi quy chưa bị xóa khi chưa xác minh được bản ZIP
gốc thay thế. Không xóa bằng chứng độc nhất chỉ để giảm dung lượng. Lịch sử đầy đủ
ở [checkpoint trước chặng](https://github.com/momentum448-glitch/Poe2viethoa/blob/e4ac909629db04b770be8b17b1aacd17f64698fd/HANDOFF_CURRENT.md).
