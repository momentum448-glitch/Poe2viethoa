# POE2 Việt Hóa — Project Guide

## Mục tiêu và quyết định đã chốt

Xây engine Việt hóa PoE2 local Windows, bắt đầu từ Story Dialogue, sau đó mở rộng
sang Quest, Tutorial, UI, Skill/Passive, Item và Mechanics.

- GitHub `momentum448-glitch/Poe2viethoa` là source of truth.
- Runtime offline, dictionary-first. AI soạn dữ liệu trước khi chơi.
- Không đọc RAM, injection/hooking hoặc tự động gửi input vào game.
- Normal mode che tiếng Anh và thay bằng tiếng Việt; chỉ hiển thị match High
  không mơ hồ. Câu ngoài catalog hoặc không chắc chắn giữ tiếng Anh.
- Không dùng Remote Desktop; không nhập dictionary/corpus của dự án cũ.
- Raw English/cache/runtime DB chỉ nằm local, gitignored. Git giữ VI và provenance.
- Cập nhật Alpha bằng source ZIP thủ công; updater/EXE để sau khi Alpha ổn định.

Foreground guard kiểm tra native PoE window class trước/sau capture và trong
thời gian OCR chờ. Discovery phủ toàn client game, sau đó theo crop của popup; không dùng dải y
hay vị trí cố định. Bộ nhận diện chọn header/footer địa phương và tách cột chat. Matcher exact trước, fuzzy có ambiguity guard. Overlay Tk/Win32
click-through, topmost, dùng `WDA_EXCLUDEFROMCAPTURE` để OCR không đọc chữ Việt.
Nguồn đổi trong lúc OCR hoặc proof đang xử lý thì kết quả cũ bị loại.

## Các chặng và phạm vi xác nhận

| Phase | Trạng thái | Mốc |
| --- | --- | --- |
| 0. Signal/architecture | PASS | OCR-first |
| 1. Capture/context | PASS/LOCKED | QC 20261004_163219 |
| 2. Matching/fresh store | PASS/LOCKED | QC 20261004_175216 |
| 3. Replacement overlay | Technical + visual PASS | QC 20261004_183317 |
| 4. Local Alpha | PASS/LOCKED | Alpha.3 QC 212425 + người dùng xác nhận 21:46 (+07) |
| 5. Translation Factory | CURRENT | 196 trang/105 nhóm nguồn; Alpha.3 sửa vị trí chờ QC Windows |
| 6. Module tiếp theo | Chưa triển khai | Quest → Tutorial → UI → Skill/Passive → Item/Mechanics |

Phase 4 đã xác nhận Continue/di chuyển/Alt+Tab bình thường trên cấu hình Windows,
Python 3.12, 1920×1080 đã thử. Không mở rộng tuyên bố PASS sang DPI/máy khác.
Baseline Alpha.3 có 9 trang; lô Factory đầu thêm 7 trang, đã có QC kỹ thuật/ảnh
223644. QC đó còn một glyph nhỏ tại mép Renly cũ và Una Home dài ở 14 px.
Hai QC 2026-10-05 Alpha.2 xác nhận Home mới 19 px. Có mask Renly dính chat và
Una thấp bị gate vị trí loại. Alpha.3 đã sửa code, vẫn cần QC native; nguyên
nhân glyph ở QC 223644 riêng chưa được chứng minh.

## Chặng Act 1 hiện hành

`0.5.0-alpha.2 / act1-20261004-01` thêm 180 trang trong 7 lô nội bộ và giữ nguyên
16 trang trước. Manifest chọn 105 nhóm nguồn với đủ trang Continue; trang trùng
trong nhiều biến thể chỉ dịch một lần. Una 64, Renly 71, Finn 30, The Hooded One 31.
Không lấy vendor/combat/callout, thoại Act khác hoặc context chưa rõ để tăng số lượng.

Factory có selection theo manifest/NPC/topic, resume, thống kê coverage, bundle
đầy đủ biến thể và thuật ngữ pack. `reviewed` là soát AI/author; `approved` cần dấu
QC câu chữ của người dùng. QA cấu trúc và match exact không thay thế soát nghĩa.

Đã đạt 149 tests, 8 lô QA sạch, DB 196 records. Replay 4 QC giữ đúng 35 High cũ;
392 mẫu OCR nhiễu không khớp High sai; 71 cặp ảnh cùng trang không bị guard báo đổi.
Bố cục dùng DejaVu Sans trên Linux giữ đủ VI ở hai vị trí panel; đây không phải
đo Segoe UI native. Bản phát hành cần QC Windows trước khi khóa chặng.

Runtime hiện hành `0.5.0-alpha.3 / popup-20261005-01` giữ bộ 196 trang. Test
bao gồm góc/cạnh, cùng câu chuyển chỗ, tọa độ client và cửa sổ di chuyển trong
OCR; crop/rebase reference cùng vị trí thực tế. QC có OCR geometry và proof ở
mỗi vị trí. [Chi tiết hai QC và sửa lỗi](docs/QC_POPUP_20261005.md).

Hai entrypoint người dùng là RUN_ALPHA/SETUP_ALPHA. Normal play không giới hạn
thời gian, log có giới hạn; QC giữ 60 giây foreground và lưu proof. Worker riêng
giữ Stop/foreground responsive; lỗi vẫn đóng gói dữ liệu thu được.
Kết quả mới vào `results/`; dọn thủ công có preview, retention và pin, không
xóa dữ liệu offline hoặc file người dùng ngoài các kết quả của bản cài.

## Nguồn và kiểm tra phân phối

Pin English: `addohm/poe2-en-cn-dict@28d683c99600eb407b4e014ccaf8247532fb4607`.
Pin context: `fireMCG/Exiled-Vault@b3dd7457aa4e7f126021b8d8577f38ef205490c7`.
ID tạo từ nội dung nguồn đã chuẩn hóa; source/glossary/manifest/review digest
bảo vệ thay đổi sau soát. Source refresh cần lô/review mới; không tái sử dụng
phê duyệt cũ cho nội dung đã đổi.

Đã kiểm tra metadata hai repo upstream và [điều khoản GGG](https://www.pathofexile.com/legal/terms-of-use-and-privacy-policy)
ngày 2026-10-04. Hai repo không khai báo license trong metadata; việc nguồn công
khai không được xem là giấy phép cho nội dung game. Text/tên/nhân vật PoE2 thuộc
GGG; dự án không tự nhận được GGG phê duyệt hoặc sở hữu IP game. Raw corpus không
được đưa vào source ZIP/Git. Rà soát lại điều kiện khi thay đổi phạm vi/phân phối.

[Chi tiết chặng](docs/ROADMAP_NEXT.md) · [Factory](docs/TRANSLATION_FACTORY.md) ·
[ADR signal](docs/ADR_001_DIALOGUE_SIGNAL.md) · [ADR nguồn](docs/ADR_002_FRESH_SOURCE.md)
