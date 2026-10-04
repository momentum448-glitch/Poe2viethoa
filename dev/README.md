# Công cụ phát triển

Chạy `SOURCE_SYNC.bat` trong thư mục này để tải nguồn đã pin và build DB;
`run_tests.bat` chạy unittest. Cả hai tự chuyển cwd về root. Người dùng bình thường
chỉ cần RUN_ALPHA.bat hoặc SETUP_ALPHA.bat ở root.

Factory và cleanup chạy từ root với môi trường .venv đã cài:

```bat
.venv\Scripts\python.exe -X utf8 -m tools.translation_factory coverage --manifest translations/manifests/act1_story.json
.venv\Scripts\python.exe -X utf8 -m tools.result_cleanup
```

Cleanup mặc định chỉ preview, ghi `factory_reports/cleanup.json`. Sau khi đọc
selection, dùng `python -m tools.result_cleanup --apply`. Lặp preview nếu file,
pointer hoặc pin đổi. `--keep N` chỉ nhận N ≥5; `--pin ten-ket-qua.zip` ghim file.
Panel cung cấp cùng hành vi. Không tự dọn lúc mở app; giữ source cache, DB và venv.
