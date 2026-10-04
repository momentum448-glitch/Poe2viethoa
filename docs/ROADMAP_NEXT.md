# Chặng tiếp theo: Story Dialogue Act 1 và dọn dự án

Ngày lập: 2026-10-04. Trạng thái: **kế hoạch đề xuất, chưa triển khai chặng mới**.
Baseline: `0.5.0-alpha.1 / factory-20261004-01`, 16 đoạn đã soát, 102 kiểm thử đạt.
Nguồn và runtime tiếp tục theo [Project Guide](../PROJECT_GUIDE.md).

## Kết quả QC vừa nhận

File: `QC_PHASE4_RESULT_20261004_223644_671889.zip`.
SHA-256: `7a4ef93ce26863e798ca5c400ca0ea960c5ad816fb1a7a38e2f00f99feed4b44`.
CRC sạch; phiên bản, 16 bản dịch và fingerprint khớp bản đã phát hành.

| Kiểm tra | Kết quả |
| --- | --- |
| Thời gian game / tổng | 60 / 67,89 giây |
| Capture / OCR | 448 / 53 |
| Nhận diện / phát ra / bỏ trùng | 32 / 13 / 19 |
| Match High | 13: 11 exact, 2 fuzzy đúng trang Una Home |
| MISS / lỗi OCR / overlay / runtime | 0 / 0 / 0 / 0 |
| Ảnh bằng chứng | 12 trang khác nhau, đã xem ở kích thước gốc |
| 7 đoạn dịch mới | Đủ cả 7; rõ chữ, che tiếng Anh, không đè Continue |
| Foreground | 1 lần pause; 12 mẫu bộ đếm transient, không phải 12 lần Alt+Tab |

Hai match fuzzy đạt 96,16 và 95,78 vì chat che dòng cuối của OCR. Đối chiếu ảnh
và nguồn xác nhận đúng trang; toàn bộ tiếng Việt vẫn có trong phần render.
20 frame bị từ chối là menu hội thoại/thế giới/chat, đúng phạm vi Story Dialogue.
Event 33 không có log vì guard bỏ kết quả OCR khi foreground đổi; bộ đếm dropped=0.

**Lô 7 đoạn mới đạt kỹ thuật/hiển thị.** Còn hai việc thật cần giải quyết:

- Proof 36 của trang Renly Introduction cũ có một vệt ký tự ở mép phải mặt nạ.
  Chưa kết luận nguyên nhân; soát phần che chữ và thay đổi trang giữa frame OCR
  và frame proof. Không chỉ nới mặt nạ khi chưa kiểm tra giới hạn panel/Continue.
- Una Home dài dùng cỡ chữ 14 px. Cần cải thiện độ dễ đọc khi mở rộng dữ liệu.

Trạng thái bản dịch vẫn `reviewed`; việc gửi ZIP không tự tạo lời xác nhận của
người dùng về câu chữ. Phase 5 tiếp tục ở CURRENT, không khóa toàn bộ từ lô đầu.

## Mục tiêu chặng lớn

Một bản phát hành có thể chơi phần hội thoại đầu Act 1 rộng hơn: **mục tiêu từ
16 lên khoảng 180–220 trang đã soát**, ưu tiên Una, Renly, Finn và The Hooded One.
Số cuối cùng chốt bằng danh sách source ID/topic đủ điều kiện, không thêm câu
vendor/combat hoặc bản trùng chỉ để đạt số lượng. Nếu số trang đúng phạm vi ít
hơn mục tiêu, ghi rõ số thực và lý do; hoàn thành trọn các topic được chọn.

| NPC | Trang có metadata trong snapshot | Ý nghĩa cho việc chọn nguồn |
| --- | ---: | --- |
| Una | 109 | Có hội thoại, vendor và callout; bộ lọc sơ bộ còn khoảng 72 ứng viên |
| Renly | 88 | Có hội thoại và vendor; bộ lọc sơ bộ còn khoảng 63 ứng viên |
| Finn | 78 | Có vendor/bark và tên topic boss lẫn vào; cần đọc context, không lấy tất cả |
| The Hooded One | 131 | Có nhiều Act; chọn rõ các topic thuộc Act 1 |
| Tổng | 406 | Là ứng viên có metadata, chưa phải 406 trang Story Dialogue Act 1 |

Các con số ứng viên lấy trực tiếp từ corpus 25.062 trang theo hai snapshot đã pin.
Bộ lọc sơ bộ chỉ dùng để ước lượng; manifest theo nguồn/context là kết quả có thẩm quyền.
Giữ nguyên 16 bản dịch đã QC. Chặng này vẫn là Story Dialogue; chưa thêm Quest/UI,
dịch trong lúc chơi, updater hay EXE để tránh làm loãng mục tiêu.

## Trình tự thực hiện trong một chặng

| Bước | Công việc | Đầu ra cần có |
| --- | --- | --- |
| 1. Chốt nguồn | Liệt kê source ID theo NPC/topic/nhóm nguồn và toàn bộ trang Continue; loại bark, vendor, topic khác Act và context chưa chắc | Manifest phạm vi, số trang/từ, các mục loại trừ có lý do |
| 2. Mở rộng Factory | Tạo lô theo manifest/NPC/topic, tiếp tục lô dở, thống kê độ phủ và xuất gói review đủ ngữ cảnh | Quy trình làm 30–50 trang mỗi lô nội bộ; không nhập ID thủ công từng câu |
| 3. Dịch và soát | Dịch trọn nhóm, nhất quán giọng/tên/quan hệ/cốt truyện; đọc nguồn và trang liền kề; QA từng lô trước publish | Khoảng 180–220 trang tổng; mọi entry có nguồn, reviewer và review digest hợp lệ |
| 4. Hiển thị | Xử lý vệt mép mask; soát vùng an toàn và trang đổi khi OCR đang chạy; cải thiện đoạn dài/cỡ chữ | Toàn bộ VI không bị cắt; che đủ tiếng Anh và chừa Continue; báo rõ trang cần xử lý |
| 5. Hồi quy và dọn | Replay các QC hiện tại với catalog lớn hơn; kiểm tra trường hợp mơ hồ/chat; bỏ đường chạy cũ sau kiểm tra dependency | Test/QA đạt, dữ liệu cũ giữ nguyên, root và handoff gọn |
| 6. Phát hành | Kiểm tra bản tải sạch, setup, số records, phiên bản/hash; merge và cấp một ZIP cố định | Một build cùng checklist QC mẫu cho cả gói |

Batches 30–50 trang là đơn vị làm việc/review nội bộ, **không phải mỗi lô gửi anh
một ZIP**. Cập nhật tiến độ bằng số trang đã soát, nhóm đã xong và việc còn lại.
Chỉ đưa bản QC khi hoàn thành cả chặng, trừ khi xuất hiện một quyết định thật sự
cần người dùng chốt. Không tự gắn `approved` cho nội dung chưa được người dùng chấp nhận.

## Điều kiện hoàn thành trước khi đưa anh QC

- Manifest có source ID duy nhất, pin/context rõ ràng và đủ trang của topic đã chọn.
- QA mọi lô: 0 lỗi; cảnh báo được đọc và xử lý/giải thích từng trang, không bỏ qua hàng loạt.
- Soát nghĩa toàn bộ bản mới; không coi match exact hay QA cấu trúc là chứng nhận nghĩa dịch.
- 16 entry baseline giữ nguyên trừ sửa câu chữ được ghi rõ; DB build đủ records, không thiếu nguồn.
- Replay cả các log Alpha.1/2/3/Factory đã lưu: giữ đúng source ID cho các trang đã biết,
  không nâng chat/menu thành match High, kiểm tra ambiguity khi nhiều bản dịch gần nhau.
- Kiểm tra layout của trang ngắn/dài ở hai vị trí panel, đủ VI và không đè Continue;
  đo bằng font Windows khi xác minh cỡ chữ. Mục tiêu ưu tiên 16–22 px trên cấu hình
  đã thử; không tăng font bằng cách cắt nội dung hoặc che nút. Trang không đạt phải có xử lý rõ ràng.
- Kiểm thử thích hợp cho code thay đổi và kiểm tra dependency sau dọn; giữ các test lifecycle.
- Bản source ZIP sạch chạy được setup; runtime giữ offline; bản phát hành có version/hash cố định.

QC người dùng sau cả chặng: hai phiên 60 giây theo nhóm NPC, ưu tiên trang ngắn,
trang dài, mở/đóng Inventory và Alt+Tab; có thể chơi thường 10–15 phút để tìm MISS.
Không yêu cầu người dùng đọc lại từng trang trong một buổi. 60 giây QC vẫn giữ
nguyên; chế độ chơi thường vẫn không giới hạn thời gian.

## Kế hoạch dọn file theo dependency thực tế

Lượt lập kế hoạch **chưa xóa file**. Việc dọn thực hiện trong chặng, trước bản
phát hành mới, có diff và kiểm tra hồi quy. Chỉ xử lý trong repo/thư mục kết quả
được chỉ định; không suy đoán hoặc xóa các thư mục khác trên máy người dùng.

| File/nhóm | Hành động dự kiến | Điều kiện và phần cần giữ |
| --- | --- | --- |
| `QC_PHASE2.bat`, `app/phase2_probe.py` | Retire khỏi bản hiện hành | Probe cũ lặp vòng capture/OCR; panel/shared runtime đã thay thế. Kiểm tra import/reference trước khi bỏ; lịch sử còn trong Git |
| `QC_PHASE3.bat`, `app/phase3_probe.py` | Retire entrypoint cũ sau khi bảo đảm panel/đường chạy kiểm thử đủ dùng | `phase3_probe` là wrapper shared runtime, không xóa `app/session_runtime.py` |
| `tests/test_phase3_probe.py` | Đổi tên thành test shared runtime, sửa tên/path fixture lỗi thời | Test này thực tế kiểm tra `session_runtime`; giữ toàn bộ kiểm thử lifecycle/foreground/Stop/ZIP |
| `SOURCE_SYNC.bat`, `run_tests.bat` | Chuyển vào `dev/` | Đây là công cụ còn dùng, không phải rác; sửa cwd, hướng dẫn và thông báo tương ứng; chức năng sync/build vẫn có |
| `RUN_ALPHA.bat`, `SETUP_ALPHA.bat` | Giữ ở root | Hai điểm vào cho người dùng: chạy bình thường và thiết lập lại |
| README | Rút lịch sử dài khỏi trang chạy hiện tại | Giữ setup, cách chơi/QC, phiên bản, độ phủ và link hướng dẫn |
| PROJECT_GUIDE | Giữ quy tắc và roadmap; rút số liệu QC lặp | Không bỏ quyết định offline/OCR/pins/không Remote Desktop/không dữ liệu cũ |
| HANDOFF_CURRENT | Rút còn trạng thái mới nhất, bằng chứng cần thiết, việc tiếp theo | Mục tiêu dưới 200 dòng; lịch sử đầy đủ vẫn tra Git, không mất checkpoint PASS |
| ADR, tài liệu Factory, kế hoạch này | Giữ, sửa link nếu cần | Là kiến trúc và quy trình còn hiệu lực; không xóa chỉ vì có ngày cũ |
| `translations/dialogue_vi.json`, glossary, `translations/batches/`, source lock | Giữ | Là dữ liệu/provenance đang dùng; không xóa batch đã publish để giảm số file |
| `app/`, `tools/`, các test đang được import/chạy | Giữ | Chỉ bỏ module sau khi chứng minh superseded và thay thế đủ hành vi |
| ZIP kết quả và `diagnostics/` cũ | Gom output mới vào `results/`, dọn có dry-run | Giữ tối thiểu 5 ZIP gần nhất, mọi QC được pin làm mốc PASS và file kết quả cuối cùng; đọc được đường dẫn cũ khi chuyển |
| Ảnh QC đã giải nén/các contact sheet tạm | Xóa bản trùng khi đủ điều kiện | Bản ZIP gốc CRC/SHA hợp lệ phải còn, và giữ log/metadata/summary làm replay; không xóa bằng chứng duy nhất |
| `__pycache__`, file tạm của phiên đã kết thúc | Có thể dọn | Không đụng file/lock đang dùng; liệt kê file và dung lượng trước khi apply |
| `source_data/`, `runtime/`, môi trường Python | Giữ dữ liệu đang hoạt động | Cần chạy offline; không xóa bừa cache/DB/dependencies và buộc người dùng tải lại |

Công cụ dọn kết quả phải xuất danh sách/bytes theo dry-run, bảo vệ phiên đang
chạy, file cuối cùng, mốc QC được giữ và chỉ xóa các đường dẫn đã liệt kê khi apply.
Không tự xóa kết quả cũ mỗi lần mở app. Không gộp dọn repo với xóa file người dùng.

Trong workspace kiểm tra hiện tại, các bản QA đã giải nén chiếm khoảng 222 MiB,
gồm cả phiên mới và các phiên hồi quy. Đây là số đo workspace của phiên phát triển,
không phải số đo máy Windows của người dùng; chưa đưa chúng vào diện xóa khi còn
cần replay hoặc chưa xác minh bản ZIP gốc và checkpoint thay thế.

## Checkpoint và hành động mở đầu

GitHub tiếp tục là nơi lưu dự án. Kế hoạch/QC này chỉ đổi tài liệu, không đổi
fingerprint runtime và không tạo bản tải nhỏ mới. Khi bắt đầu triển khai, tạo
nhánh chặng mới từ main, lập manifest nhóm thoại Act 1 và thống kê số trang hợp
lệ trước; tiếp đó làm Factory, dịch/soát, layout, cleanup và kiểm thử trong cùng
chặng. Handoff ghi tiến độ theo nhóm và số trang để hội thoại mới tiếp quản được.
