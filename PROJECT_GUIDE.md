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

Kiến trúc trên **chưa khóa** ở nhánh log/OCR cho Dialogue. Spike 001 quyết định.

## Roadmap

### Phase 0 — Signal & architecture validation
- Spike 001: Client.txt + OCR + layout evidence.
- Chốt Log-first / OCR-first / Hybrid cho Dialogue.

### Phase 1 — Core capture/context
- game focus/window detection;
- screen capture;
- frame-change/stability gate;
- log tailer;
- diagnostics.

### Phase 2 — Dialogue v0.1
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
