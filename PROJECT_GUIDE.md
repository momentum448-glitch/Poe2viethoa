# POE2 Việt Hóa — Project Guide

## North Star

Xây một engine Việt hóa Path of Exile 2 chạy local trên Windows, bắt đầu bằng Story Dialogue và có thể mở rộng theo module sang Quest, Tutorial, UI, Skill/Passive, Item và Mechanics.

## Nguyên tắc đã chốt

- GitHub `momentum448-glitch/Poe2viethoa` là source of truth.
- Alpha phục vụ người dùng chính trước, nhưng kiến trúc hướng tới khả năng phát hành cộng đồng.
- Runtime offline, dictionary-first; không dùng AI model để dịch trực tiếp trong lúc chơi.
- Không đọc RAM, không injection/hooking, không tự động gửi input vào game.
- Overlay Normal mode hướng tới **che text tiếng Anh và thay bằng tiếng Việt**.
- Khi match không chắc chắn: Normal mode không hiện; Debug mode được phép hiện candidate/confidence.
- Translation source giữ dạng dễ review trong Git; runtime database có thể build sang SQLite sau.
- Alpha cập nhật dữ liệu bằng release thủ công; updater để sau.
- Python/source-first; đóng EXE sau khi Local Alpha ổn định.

## Kiến trúc mục tiêu sơ bộ

```text
                  POE2
                   │
        ┌──────────┴──────────┐
        │                     │
   Client.txt               Screen
        │                     │
 area / events          Capture Scheduler
 NPC signal?                 │
        │              Frame Stabilizer
        │                     │
        │                    OCR
        │                     │
        └──────────┬──────────┘
                   ↓
            Context Resolver
                   ↓
             Candidate Index
                   ↓
          Exact / Fuzzy Matcher
                   ↓
            Translation Store
                   ↓
          Replacement Overlay
```

### Dialogue signal decision — LOCKED

Spike 001 + 001B–001C đã chốt **OCR-first** cho Story Dialogue.

- OCR là nguồn text chính.
- Screen/layout context là nguồn context chính.
- `Client.txt` không phải runtime dependency.
- Nếu sau này tìm được log ổn định, log chỉ được thêm như optional context adapter; engine không được phụ thuộc vào nó.

Lý do: real QC đã chứng minh Windows OCR đọc tốt nhiều câu story của Renly với bounding box ổn định ở cả normal và inventory-open layouts, trong khi nhiều probe độc lập không tìm được một `Client.txt` đáng tin cậy trên máy test.

## Roadmap

### Phase 0 — Signal & architecture validation
- Spike 001: Client.txt + OCR + layout evidence. **PASS**
- Dialogue signal architecture: **OCR-first — LOCKED**.

### Phase 1 — Core capture/context — PASS / LOCKED
- game foreground detection;
- screen capture;
- dialogue-panel/layout detection;
- frame-change/stability gate;
- OCR adapter + bounding boxes;
- diagnostics/evidence capture;
- one-click QC packager.
- optional log adapter may be explored later, but is not on the critical path.

### Phase 2 — Dialogue matching + translation store — CURRENT
- Clearfell dataset;
- normalization;
- candidate index;
- exact then fuzzy matching;
- confidence policy.

### Phase 3 — Replacement overlay
- text bounding box;
- mask/cover original English;
- fit Vietnamese text;
- click-through/topmost;
- DPI handling;
- self-capture protection.

### Phase 4 — Local Alpha
- setup;
- run;
- diagnostics;
- test on real PoE2 sessions.

### Phase 5 — Translation Factory
- extraction;
- glossary/canon;
- AI draft;
- automated QA;
- review state;
- version-independent translation memory keyed by source/context.

### Phase 6 — Additional modules
Quest → Tutorial → UI → Skill/Passive → Item/Mechanics.

## External projects worth studying

- Denzeriko/RuneHelper: OCR scheduling, frame stability, row cache, diagnostics, overlay architecture.
- MaxDistroyer/MaxOverlay-POE2: MSS + Windows OCR + positional lines + candidate indexing.
- Lailloken/Exile-UI: Client.txt area/context/dialogue signals.
- uezer/OverlayTranslate: replacement-style translated text over original screen text.
- EsintisiYeter/poe2-turkce-yama: translation memory, glossary, QA and patch-resilient text matching.

## Rule for future work

Do not assume old code or old guide claims are still correct. Revalidate important behavior against the current PoE2 client and keep evidence under tests/diagnostics.
