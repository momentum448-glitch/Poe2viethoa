# POE2 Việt Hóa

Overlay Việt hóa hội thoại Path of Exile 2, chạy local trên Windows.
**0.5.0-alpha.2 / act1-20261004-01** có **196 trang Story Dialogue Act 1**
đã soát nghĩa, tăng 180 trang và giữ nguyên 16 trang của bản trước.

| NPC | Trang trong bộ chạy |
| --- | ---: |
| Una | 64 |
| Renly | 71 |
| Finn | 30 |
| The Hooded One | 31 |

Manifest có 105 nhóm nguồn, bao gồm các biến thể nhiệm vụ và trang dùng chung.
Đây là phạm vi đã chọn, không phải toàn bộ hội thoại Act 1 hoặc 105 mục menu
khác nhau. Vendor/combat/callout và các nhóm chưa xác định context được loại.
Các trang ngoài bộ dịch giữ tiếng Anh. Khi chơi, tool tra SQLite offline;
AI chỉ dùng trong giai đoạn soạn và soát bản dịch.

## Chạy và gửi QC

1. Giải nén bản mới vào một thư mục mới, mở **RUN_ALPHA.bat**.
2. Lần đầu cần mạng để cài dependencies và tải nguồn đã pin. Cần Python 3.10+
   và Windows 10 build 19041+; cấu hình đã QC dùng Python 3.12, 1920×1080.
   Những lần sau chạy offline. Dùng **SETUP_ALPHA.bat** nếu cần thiết lập lại.
3. Chọn **Bắt đầu**, chuyển sang PoE2. Chế độ chơi chạy đến khi bấm Dừng.
4. Alt+Tab quay lại panel, bấm **Dừng & tạo ZIP**, rồi **Mở file kết quả**.

**QC 60 giây** tính thời gian PoE2 ở foreground, lưu ảnh vùng hội thoại và tạo
`results/QC_PHASE4_RESULT_*.zip`. Chế độ chơi tạo `results/ALPHA_RESULT_*.zip`
với log nhẹ, không lưu ảnh. Panel đọc được con trỏ kết quả cũ ở root.
Nếu bấm Dừng sớm, QC là `INTERRUPTED`. `TECHNICAL_PASS` vẫn cần xem ảnh và
xác nhận thao tác thực tế; nó không tự chứng nhận câu chữ.

QC bản này theo hai phiên, tùy topic anh đã mở trong game:

- Una / Renly: ưu tiên Home, Fatherhood, các trang dài và Introduction cũ.
- Finn / The Hooded One: chọn các topic Act 1 đang có; thử trang ngắn và dài.

Giữ mỗi trang 3–4 giây, thử mở/đóng Inventory và Alt+Tab. Gửi ZIP kết quả trong
chat. Nếu NPC/topic chưa mở, thử phần đang có và tiếp tục chơi thường để tìm
MISS. Nếu panel không mở, gửi `ALPHA_STARTUP_ERROR.txt` khi file này được tạo.

## Thay đổi và xác minh

- Factory chọn/resume theo manifest, NPC hoặc topic; giữ đầy đủ trang Continue
  kể cả trang bị dedupe trong corpus. Bản soát có glossary/context và review digest.
- Runtime bỏ kết quả nếu nguồn đổi trong lúc OCR xử lý, ẩn bản dịch khi glyph
  đổi và kiểm tra lại nguồn sau khi chụp proof. Nới mép che chữ, dùng khoảng
  trống đã đo phía trên Continue cho câu dài; cỡ chữ tối đa 22 px.
- Bỏ launcher/probe Phase 2/3 cũ; giữ kiểm thử shared runtime. Công cụ phát
  triển chuyển vào `dev/`; tài liệu hiện hành được rút gọn.
- **128 kiểm thử đạt**, 8 lô QA không lỗi/cảnh báo, DB đủ 196 records. Replay
  4 log QC giữ đúng 35 High cũ; 392 mẫu lỗi OCR không có High khớp sai trang.

Bản mới chưa được QC native Windows. Kiểm tra font Linux là kiểm tra bố cục
bổ sung, không thay thế Segoe UI/PoE2 trên máy người dùng. Cần kiểm tra lại vệt
mép Renly cũ và Una Home dài; nguyên nhân vệt cũ chưa được chứng minh.
Phase 4 vẫn PASS/LOCKED trên cấu hình đã thử; Phase 5 ở CURRENT.

## Dọn kết quả cũ

Bấm **Ghim kết quả này** để giữ một ZIP. **Dọn kết quả cũ** hiện danh sách và
ước lượng dung lượng trước khi xóa. Tool giữ ít nhất 5 ZIP mới nhất, kết quả
cuối của Alpha/QC, file đã ghim và các mốc QC đã chốt. Không tự dọn khi mở app.
Chỉ xóa chẩn đoán đi kèm khi toàn bộ file là bản trùng đã xác minh trong ZIP.
File độc nhất, symlink và ZIP hỏng được giữ; dọn bị chặn khi phiên overlay đang chạy.

[Quy tắc dự án](PROJECT_GUIDE.md) · [Factory](docs/TRANSLATION_FACTORY.md) ·
[Chặng vừa triển khai](docs/ROADMAP_NEXT.md) · [Handoff](HANDOFF_CURRENT.md)
