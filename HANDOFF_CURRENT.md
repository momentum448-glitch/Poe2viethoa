# Handoff — POE2 Việt Hóa

## Trạng thái hiện hành

Build **0.5.0-alpha.3 / popup-20261005-01**. Đã sửa vị trí hộp thoại NPC theo
phản hồi và hai ZIP QC 2026-10-05. Bản sửa chờ QC native Windows; không tự khóa
Phase 5. Người dùng đã cho thực thi chặng và GitHub/source ZIP; không hỏi lại
các bước đã được cho phép.

GitHub `momentum448-glitch/Poe2viethoa` là nguồn chính. Python/source ZIP chạy
local, gửi QC 60 giây. Không Remote Desktop; không dùng dictionary/corpus 208
dòng của dự án cũ; không AI dịch trong game. Repo artifacts giữ trong GitHub.

| Phase | Mốc đã giữ |
| --- | --- |
| 1 | PASS/LOCKED QC 163219 |
| 2 | PASS/LOCKED QC 175216 |
| 3 | Technical + visual PASS QC 183317 |
| 4 | PASS/LOCKED Alpha.3 QC 212425; user xác nhận Continue/di chuyển/Alt+Tab 21:46 (+07) |
| 5 | CURRENT; 196 trang reviewed; Alpha.3 runtime mới chờ QC |

Cấu hình QC thực tế Windows/Python 3.12/1920×1080. Test đa độ phân giải không
thay thế native QC ở máy/DPI/monitor khác. Lịch sử cũ tại
[checkpoint e4ac909](https://github.com/momentum448-glitch/Poe2viethoa/blob/e4ac909629db04b770be8b17b1aacd17f64698fd/HANDOFF_CURRENT.md).

## Hai QC vừa đọc và nguyên nhân lỗi vị trí

Cả hai đúng Alpha.2/DB196, CRC sạch, fingerprint
`fa03f2605f5367a7a37716c1b77af9d8ade933ecd96c496a453560c63070bbfd`.

| QC_PHASE4_RESULT | Capture / OCR | Detection / emit | High / MISS | Proof / lỗi |
| --- | ---: | ---: | ---: | ---: |
| 20261005_070347_126657 | 445 / 45 | 24 / 13 | 13 / 0 | 12 / 0 |
| 20261005_070508_093981 | 459 / 52 | 19 / 10 | 5 / 5 | 4 / 0 |

Mỗi phiên 60 giây game, 62,34/63,00 tổng; stale skips 12/6, transient samples
8/9, không pause/drop. TECHNICAL_PASS không bao phủ mọi popup hoặc approval câu.

- ROI cố định `(230,421,1190,486)` và các gate body 82%/Continue 90%/header 33%
  gây mất Una thấp. Raw 070347 events 38/45, 070508 events 9/16 xác nhận hội
  thoại thật/Continue dưới nhưng log no_dialogue_anchor.
- Renly events 6/9/12 dính chat, source match đúng nhưng mask lấn header/chat.
- Finn event 26 speaker sai `what`; cùng body ở event 29 có Finn vẫn MISS.
- Cùng page Una events 3/20 đã đổi vị trí, proof cũ chỉ dedupe theo page ID.
- Đã xem đủ 16 native proofs: ngoài 3 mask Renly nói trên, đủ VI/chừa Continue,
  chưa thấy glyph mép sót. Renly 20–22 px, Una/Finn 19–21; Home mới 19 px.

SHA ZIP gốc, ảnh, số liệu và giới hạn: [QC 20261005](docs/QC_POPUP_20261005.md).
Không sửa/xóa các ZIP bằng chứng gốc. Đây là QC Alpha.2, không phải Alpha.3.

## Runtime Alpha.3

- Discovery toàn client PoE2 foreground; track crop theo body/header/footer.
  Nguồn đổi hoặc popup chuyển/đóng: ẩn overlay và tìm lại toàn client.
- Khoảng cách/cột theo font và baseline, không theo ROI/screen band. Tách word
  boxes khi OCR nối chat với body; word box cao bất thường không cắt mất dòng.
  Header chỉ nhận tên NPC catalog, dùng đúng Continue thuộc paragraph.
- Lấy bounds Win32 physical pixel; kiểm tra HWND+bounds trong capture/OCR/proof.
  Cửa sổ move/resize làm mất hiệu lực kết quả cũ. Bounds lỗi thì đợi.
- Crop/rebase reference và body box cùng nhau. Dedupe có tọa độ tuyệt đối;
  cùng trang chuyển vị trí vẫn show lại. Proof theo page+vị trí, chịu OCR jitter.
- QC logs có capture_region/capture_mode, OCR lines/word boxes, proof path.
  Normal Alpha vẫn không lưu ảnh; logs bounded. Stats có discovery/tracking OCR.
- Oversized discovery dùng engine MaxImageDimension, map boxes về pixel gốc.
  Overlay phủ virtual desktop cho origin âm; multi-monitor chưa QC native.
- Giữ foreground/Stop/self-capture/glyph guards, runtime lock và error packaging.
  Padding 18 px, dùng khoảng trống trên Continue, tối đa 22 px, không cắt VI.

## Dữ liệu và dọn đã hoàn tất

196 trang: Una 64, Renly 71, Finn 30, Hooded 31. Thêm 180 trong 7 lô nội bộ,
giữ nguyên 16 baseline. 105 nhóm nguồn/biến thể, không phải 105 topic menu.
Manifest giữ page IDs/order/full group hash/shared pages/source lock/terms;
review digest gắn manifest. Mới đều reviewed, chưa tự gắn approved.

Nguồn không đổi: `addohm/poe2-en-cn-dict@28d683c99600eb407b4e014ccaf8247532fb4607`,
`fireMCG/Exiled-Vault@b3dd7457aa4e7f126021b8d8577f38ef205490c7`.
Không commit raw English/cache/DB. Factory pack/coverage/resume/bundle đã có.
Metadata upstream/GGG terms xem 2026-10-04; không tự nhận license/IP/phê duyệt GGG.

Đã bỏ QC_PHASE2/3.bat và probe cũ; giữ lifecycle tests, dev scripts ở dev/.
ZIP mới vào results/, LAST_* compatibility. Panel có pin/cleanup preview,
giữ ≥5 mới nhất + LAST + pin + checkpoint. Chặn active session/symlink/ZIP hỏng;
chỉ xóa diagnostics khi là exact duplicate ZIP. Không tự dọn PC người dùng.

## Xác minh và bước tiếp

**149 tests đạt**, compile/diff checks sạch. Geometry tests: mọi góc/cạnh/giữa
1366–3840, origin âm/windowed, crop/reference, same-page relocation/second proof,
window move during OCR, resize map, Stop/Alt+Tab/stale-proof và chat.
196/196 exact đúng ID; 8 batch QA 0 lỗi/cảnh báo. Translation/source/manifest
không đổi trong release này. Các mốc 35 High/392 nhiễu/71 cặp guard trước vẫn
được lưu; không coi là live game hoặc đo tốc độ native của bản mới.

Replay phụ Tesseract trên 97 raw PNG mới giữ 18/18 emitted High cũ đúng ID,
không ID High khác trong tập so sánh, không layout error. Phục hồi Una thấp và
speaker Finn/tách chat. Không phải replay chính xác Windows OCR cũ (chưa lưu
word boxes), không thay QC native. Alpha.3 logs sẽ đủ geometry cho lần sau.

5 MISS Finn là 3 câu duy nhất: Clearfell lặp ba lần chưa exact trong source pin;
2 Introduction có source nhưng thiếu context và ngoài manifest. Gom vào chặng
nguồn/context/biến thể tiếp, không nới matcher để giả pass. Chi tiết ID ở report.

Gửi một source ZIP cho bản sửa; người dùng thử cùng NPC từ nhiều hướng, Inventory,
Una thấp, trang dài/Continue, đóng/mở cùng câu và Alt+Tab trong QC60s. Chỉ chốt
PASS khi có bằng chứng Windows phù hợp; chỉ approved khi có xác nhận câu chữ.
Fingerprint bản sửa: `6366ef324adb2769412e5e5f36c6cdf450f4be629db8fdff1ca198396cc8c1fd`.
Nguồn ZIP phát hành theo Git commit; giữ handoff dưới 200 dòng.

[README](README.md) · [Guide](PROJECT_GUIDE.md) · [Factory](docs/TRANSLATION_FACTORY.md)
· [chặng Act 1](docs/ROADMAP_NEXT.md) · [QC vị trí](docs/QC_POPUP_20261005.md)
