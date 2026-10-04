# QC Spike 001 — Cách chạy đơn giản

## Anh chỉ cần 3 bước

### 1. Tải repo

Vào repo `momentum448-glitch/Poe2viethoa` → **Code → Download ZIP**.

Giải nén ZIP ra một thư mục bình thường, ví dụ Desktop.

### 2. Chạy QC

Mở PoE2 trước, đứng gần một NPC có hội thoại story.

Nhấp đúp:

```text
QC_START.bat
```

Lần chạy đầu script sẽ tự:

- tạo Python virtual environment;
- cài dependency cần thiết;
- chạy Signal Audit trong 120 giây.

Trong lúc cửa sổ QC đang chạy:

1. quay lại PoE2;
2. nói chuyện với một NPC story;
3. chuyển qua tối thiểu 3–5 câu;
4. giữ mỗi câu 1–2 giây;
5. nếu tiện, thử một đoạn khi inventory đóng và một đoạn khi inventory mở.

Không cần ghi chép thủ công.

### 3. Gửi kết quả

Khi xong, Windows Explorer sẽ tự mở và chọn file dạng:

```text
QC_RESULT_YYYYMMDD_HHMMSS.zip
```

**Kéo thả nguyên file ZIP đó vào chat.**

Không cần mở ZIP, không cần gửi từng screenshot hoặc log.

## Em sẽ đọc gì trong ZIP?

- `summary.json`: thống kê session;
- `client_new.log`: log PoE2 phát sinh trong lúc test;
- `zone_events.jsonl`: area IDs;
- `log_candidates.jsonl`: các dòng giống NPC dialogue;
- `ocr_frames.jsonl`: OCR text + bounding boxes;
- `screenshots/`: bằng chứng hình ảnh tương ứng;
- `overlap_candidates.json`: đối chiếu sơ bộ giữa log và OCR.

Từ đó sẽ chốt một trong ba kiến trúc:

- **Log-first**
- **OCR-first**
- **Hybrid log + OCR**

## Nếu có lỗi

### Báo chưa có Python

Dừng tại đó và gửi ảnh cửa sổ QC. Không cần tự cài linh tinh. Bản QC portable/EXE sẽ được chuẩn bị nếu cần.

### Tool không tìm thấy Client.txt

Vẫn cứ hoàn thành QC. Screenshot và OCR vẫn được thu. Sau đó gửi ZIP, đường dẫn log sẽ được xử lý ở vòng kế tiếp.

### OCR lỗi

Vẫn gửi ZIP. Spike được thiết kế để phần log/screenshot không chết theo OCR.
