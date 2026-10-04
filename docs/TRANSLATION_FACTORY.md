# Translation Factory — Act 1 pack

Build `0.5.0-alpha.2 / act1-20261004-01` có 196 trang trong 105 nhóm nguồn,
180 trang mới qua 7 lô nội bộ, giữ nguyên 16 trang trước.

## Dữ liệu và trạng thái

| State | Ý nghĩa | Runtime |
| --- | --- | --- |
| draft | Nháp cần đọc nguồn/soát nghĩa | Không publish |
| reviewed | AI/author đã soát toàn nguồn/context và QA đạt | Được dùng trong Alpha |
| approved | Có dấu QC câu chữ của người dùng | Được dùng, chặn downgrade |

`translations/glossary.json` là style/terms nền; manifest thêm scope và terms pack.
Renly ta/con chỉ trong biến thể con nuôi; người lạ tôi/bạn. Proper names giữ nhãn
English. Các quyết định về sự chưa chắc, nói bỏ lửng và quan hệ phải dựa trên nguồn.
Đây là glossary dự án, không phải bản Việt hóa chính thức.

Batches chỉ lưu VI/ID/hash/context/review notes và base catalog digest. Raw English
ở ignored source_data/, review bundles ở ignored factory_reports/. QA source,
placeholders/numbers, names, context, duplicates, drift/tampering không thay thế
soát nghĩa. Fuzzy/TM chỉ gợi ý reference, không tự điền hoặc publish câu khác.

## Chọn cả gói và tiếp tục lô dở

Chạy từ root, prefix Windows là `.venv\Scripts\python.exe -X utf8 -m`;
ví dụ dưới dùng `python -X utf8 -m`. Nếu thiếu nguồn, dùng `dev/SOURCE_SYNC.bat`.

```bat
python -X utf8 -m tools.translation_factory pack --manifest translations/manifests/act1_story.json --output-dir translations/batches --size 40
python -X utf8 -m tools.translation_factory coverage --manifest translations/manifests/act1_story.json
```

Thêm `--speaker Una` hoặc `--topic Home_1` để lọc theo metadata nguồn; có thể lặp.
Topic filter có suffix riêng để không đè lô toàn gói. Manifest giữ source ID/hash
của từng page và hash/order/page_ids của nhóm gốc. Validator đối chiếu snapshot
cache theo pin, không chỉ tin segment_count ở corpus đã dedupe. Thiếu/đảo Continue,
source/context khác hoặc hash manifest đổi thì phải xử lý trước khi resume/review.

Cỡ 40 là giới hạn lô; nhóm không bị cắt để đủ số. Lô cuối theo NPC có thể nhỏ hơn.
Layout dùng baseline_ids bất biến trong manifest: publish lô trước không đổi tên
hay selection các lô sau. Chạy lại pack resume lô đúng selection, không ghi đè VI.
Coverage `complete_groups/groups` đếm nhóm nguồn/biến thể, không phải mục menu game.

## Soạn, review và publish

```bat
python -X utf8 -m tools.translation_factory bundle --batch translations/batches/my-batch.json --output factory_reports/my-batch.md
python -X utf8 -m tools.translation_factory qa --batch translations/batches/my-batch.json
python -X utf8 -m tools.translation_factory mark-reviewed --batch translations/batches/my-batch.json --reviewer AI_or_author --note "Read complete source/variants; explain choices."
python -X utf8 -m tools.translation_factory publish --batch translations/batches/my-batch.json
```

Người soạn đọc đủ source/Continue và mọi biến thể chứa shared page, rồi sửa `vi`
và draft notes. Không sửa ID/hash/context hoặc tự đổi status. Bundle chứa glossary,
style pack, neighboring original pages và same-speaker reviewed TM. AI drafting
hiện thực hiện trong chat, chưa có bulk AI API client.

QA trả 0 khi đạt, 1 khi có lỗi, 2 khi command/input hỏng. Draft rỗng không đạt;
cảnh báo độ dài cần đọc từng trang. `mark-reviewed` chỉ sau soát nghĩa thực tế.
Review digest bind source, VI, context, glossary/source lock và manifest. Catalog
publish atomic, idempotent khi không đổi, chặn conflict trong thời gian review và
chặn downgrade approved. Catalog editing/publish phải tuần tự.

Build DB bằng `SETUP_ALPHA.bat` hoặc `python -X utf8 -m tools.build_translation_db`.
Hash/source join lỗi giữ DB cũ. RUN_ALPHA phát hiện catalog mới và chuẩn bị lại.
Sau human QC thật, dùng `approve --batch ... --reviewer ... --note ...`, rồi publish
để promote cùng bản. Nội dung đã đổi cần lô review/approval mới.

Nếu chỉ bổ sung một tập MISS đã xác minh, đường chuẩn bị cũ vẫn có:

```bat
python -X utf8 -m tools.translation_factory prepare --batch-id my-batch --from-qc QC.zip --output translations/batches/my-batch.json
```

Lặp `--source-id ID` cho selection rõ hoặc revision. QC selection chỉ lấy exact
fresh-source MISS duy nhất; chat/fuzzy/ambiguity không được thành dữ liệu tự động.
Các batch nhỏ là đơn vị nội bộ; gom một chặng đủ lớn trước khi đưa source ZIP QC.

## Kiểm chứng hiện tại

8 lô QA 0 lỗi/cảnh báo; 196 records; 128 tests đạt. Replay giữ 35 High cũ trên
4 log và toàn bộ 196 nguồn exact đúng ID. 392 mẫu OCR noise không có High sai.
16 entry cũ giữ nguyên. Native QC/font của build mới chưa có; xem
[kết quả chặng và giới hạn](ROADMAP_NEXT.md). Không tự gắn approved cho 180 trang.
