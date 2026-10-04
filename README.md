# POE2 Việt Hóa

Local-first Vietnamese localization engine for Path of Exile 2.

## Chạy QC ngay

Để kiểm tra Spike 001 trên máy Windows:

1. Vào repo → **Code → Download ZIP**.
2. Giải nén.
3. Mở PoE2 và đứng gần NPC story.
4. Nhấp đúp **`QC_START.bat`**.
5. Nói chuyện 3–5 câu trong lúc QC chạy.
6. Khi xong, Explorer sẽ tự chọn file **`QC_RESULT_YYYYMMDD_HHMMSS.zip`**.
7. Kéo thả nguyên file ZIP đó vào chat.

Chi tiết: `docs/QC_SPIKE001.md`.

## Current phase

**Spike 001 — PoE2 Signal Audit**

Before building the runtime engine, this spike measures which signals are reliable enough to drive the Dialogue module:

1. `Client.txt` events and NPC dialogue coverage.
2. Stable area/zone detection from `Generating level ... area "..."` log lines.
3. Windows OCR quality and bounding boxes for story dialogue.
4. Screen-state/layout behavior for dialogue placement.

The result of this spike will decide whether Dialogue v0.1 is **log-first**, **OCR-first**, or **hybrid**.

## Project principles

- GitHub is the source of truth.
- Runtime is local and offline.
- No process-memory reading, DLL injection, game hooking, or automated game input.
- Start with Story Dialogue, but keep the engine modular for Quest, Tutorial, UI, Skill/Passive, Item and Mechanics modules later.
- Translation source data stays human-readable in Git; runtime formats can be built from it later.

## Developer / manual Spike setup

On Windows 10/11 with Python 3.10+:

```bat
setup_spike001.bat
run_spike001.bat
```

The spike writes a timestamped evidence bundle under `diagnostics/spike001/`.

See `docs/SPIKE_001_SIGNAL_AUDIT.md` for the technical protocol.

## Repository status

This repository is being rebuilt cleanly. Previous project code is reference material only until individually revalidated.
