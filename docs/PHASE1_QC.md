# Phase 1 — Core Capture + Dialogue Context

## Goal

Prove that the OCR-first core can run continuously without wasting OCR calls or confusing nearby PoE2 UI with story dialogue.

## Components under test

```text
POE2 foreground?
      ↓ yes
Capture dialogue ROI
      ↓
Frame changed?
      ↓ yes
Wait until settled
      ↓
Windows OCR
      ↓
Dialogue detector
      ↓
normal_right / inventory_left / not-dialogue
```

## Real-QC protocol

Run `QC_PHASE1.bat`.

During the 90-second window:

1. keep PoE2 in the foreground;
2. open one story NPC;
3. show 3–5 dialogue passages;
4. leave each passage visible briefly;
5. if convenient, switch inventory open/closed during different passages;
6. briefly return to the NPC topic menu so false-positive rejection is tested too;
7. let the tool finish naturally.

The result ZIP contains:

- `metadata.json`;
- `summary.json`;
- `events.jsonl`;
- `screenshots/`;
- `errors.jsonl` only if OCR/runtime errors occur.

## Pass criteria

- `ocr_calls < captures` by a wide margin;
- unchanged dialogue does not continuously re-trigger OCR;
- story dialogue is detected with useful bbox;
- topic-selection menu is not accepted as story dialogue;
- global chat is not merged into dialogue;
- both observed layouts classify correctly when tested;
- zero recurring OCR exceptions.

## After pass

Phase 2 connects:

```text
DialogueContext.text
    ↓
normalization
    ↓
candidate index
    ↓
exact match
    ↓ fallback
fuzzy match
    ↓
confidence policy
    ↓
Vietnamese translation store
```
