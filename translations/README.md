# Dữ liệu Việt và provenance

Catalog hiện hành có **196 trang reviewed**: giữ 16 trang trước, thêm 180 qua
7 lô Act 1. Una 64, Renly 71, Finn 30, The Hooded One 31. Manifest chứa 105 nhóm
nguồn/biến thể với đầy đủ Continue, trang dùng chung chỉ dịch một lần.

- `dialogue_vi.json`: catalog VI được publish vào runtime.
- `glossary.json`: thuật ngữ/style nền, giữ nguyên để bảo toàn review lô cũ.
- `manifests/act1_story.json`: phạm vi, nguồn/context/order, baseline và terms pack.
- `batches/*.json`: nháp/reviewer/review notes/digest, giữ kể cả sau publish.

Raw English không commit. `dev/SOURCE_SYNC.bat` tải pin từ sources.lock.json vào
ignored source_data/ rồi build runtime/translations.sqlite3. Không import dictionary
của dự án cũ. ID ổn định theo nguồn đã chuẩn hóa; source change cần ID/review mới.
Review bundles chứa English ở ignored factory_reports/, không đưa vào source ZIP.

`draft` không vào Normal runtime. `reviewed` là soát AI/author và QA; `approved`
cần human QC câu chữ có ghi nhận. QA/match exact không tự chứng nhận nghĩa dịch.
Source/VI/hash/context và manifest bind review. Đổi sau review bị chặn. Chín entry
Alpha đầu giữ nguyên format cũ, bảy entry Factory trước và 180 mới có provenance.

[Quy trình Factory](../docs/TRANSLATION_FACTORY.md) · [Nguồn và quyết định](../PROJECT_GUIDE.md)
