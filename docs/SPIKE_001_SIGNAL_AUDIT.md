# Spike 001 — PoE2 Signal Audit

## Câu hỏi cần trả lời

Dialogue v0.1 nên dùng nguồn nhận dạng nào?

- **Log-first**: `Client.txt` chứa đủ story dialogue để dùng làm text signal chính.
- **OCR-first**: story dialogue không có trong log hoặc log quá thiếu; OCR là text signal chính.
- **Hybrid**: log cung cấp area/NPC/event context, OCR cung cấp text hiển thị và bounding box.

Khuyến nghị hiện tại trước khi test: **Hybrid**, nhưng chưa khóa.

## Bằng chứng Spike 001 thu thập

Mỗi session tạo một thư mục:

```text
diagnostics/spike001/YYYYMMDD_HHMMSS/
├── metadata.json
├── client_new.log
├── log_candidates.jsonl
├── zone_events.jsonl
├── ocr_frames.jsonl
├── screenshots/
└── summary.json
```

### Client.txt

Tool tự thử các vị trí phổ biến trên Windows, gồm:

- `Documents\My Games\Path of Exile 2\logs\Client.txt`
- Steam `...\steamapps\common\Path of Exile 2\logs\Client.txt`
- Standalone GGG `...\Grinding Gear Games\Path of Exile 2\logs\Client.txt`

Có thể chỉ định thủ công:

```bat
.venv\Scripts\python.exe spikes\spike001_signal_audit.py --log "D:\...\logs\Client.txt"
```

### OCR

Spike dùng Windows Media OCR qua PyWinRT và chụp màn hình bằng MSS.

Mặc định OCR một vùng tương đối lớn quanh khu vực dialogue để ưu tiên thu bằng chứng hơn hiệu năng. Chỉ lưu frame khi text OCR thay đổi.

## Protocol test chuẩn

1. Chạy PoE2 ở **Windowed Fullscreen**, ưu tiên 1920×1080 cho vòng đầu.
2. Đứng ở khu vực có NPC story, ví dụ Clearfell.
3. Chạy `run_spike001.bat`.
4. Trong vòng 120 giây:
   - mở NPC;
   - chọn một topic có story dialogue;
   - để mỗi câu hiện đủ lâu khoảng 1–2 giây;
   - chuyển qua tối thiểu 3–5 câu;
   - nếu có thể thử cả trạng thái inventory đóng và mở;
   - đóng hội thoại.
5. Đợi tool tự kết thúc hoặc nhấn Ctrl+C.

## Tiêu chí quyết định

### Chọn Log-first khi

- phần lớn câu story hiển thị trên màn hình cũng xuất hiện trong `client_new.log`;
- thứ tự/timestamp đủ sát để map sang dialogue hiện tại;
- speaker/text ổn định và ít phụ thuộc localization client.

### Chọn OCR-first khi

- story dialogue không xuất hiện trong log hoặc chỉ có rất ít;
- OCR đọc text đủ ổn định để exact/fuzzy match;
- bounding box đủ tốt để replacement overlay.

### Chọn Hybrid khi

- log bắt zone/speaker/event tốt nhưng không chứa đầy đủ text;
- OCR bắt text nhưng cần context để thu hẹp candidate;
- hai nguồn kết hợp làm confidence tăng rõ rệt.

## Những gì chưa kiểm chứng

- coverage thật của story dialogue trong `Client.txt`;
- OCR accuracy trên đúng máy, graphics settings và font scale của người dùng;
- ảnh hưởng của DPI scaling;
- vị trí dialogue khi inventory mở/đóng;
- khả năng overlay tránh self-capture.

Không khóa kiến trúc runtime trước khi có kết quả Spike 001.
