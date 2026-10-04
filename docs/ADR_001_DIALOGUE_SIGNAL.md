# ADR-001 — Dialogue Signal Architecture

**Status:** Accepted / Locked  
**Date:** 2026-10-04

## Decision

Story Dialogue v0.1 will be **OCR-first**.

The runtime must not depend on `Client.txt`.

## Evidence

Real Spike 001 QC on PoE2 at 1920×1080 showed:

- Windows OCR successfully captured at least 10 distinct Renly story-dialogue lines.
- OCR produced usable word and line bounding boxes.
- Dialogue remained readable in both the normal layout and the horizontally shifted inventory-open layout.
- OCR noise was mostly nearby chat/UI text, which is addressable with dialogue-panel/layout filtering.

Follow-up log probes did not locate a reliable `Client.txt` on the test system. V5 detected:

- running process: `PathOfExile.exe`;
- Steam roots: `e:/steam`, `E:\Steam`;
- no usable PoE2 manifest discovered by the probe;
- no reliable `Client.txt` candidate.

This is sufficient to reject `Client.txt` as a required runtime dependency.

## Runtime flow

```text
PoE2 screen
    ↓
Dialogue layout detector
    ↓
Frame-change / stability gate
    ↓
Windows OCR
    ↓
OCR line + word bounding boxes
    ↓
Dialogue text stabilizer
    ↓
Context resolver
    ↓
Candidate index
    ↓
Exact match
    ↓ fallback
Fuzzy match + confidence policy
    ↓
Vietnamese translation
    ↓
Replacement overlay
```

## Consequences

### Positive

- Works from visible pixels only.
- No dependence on an undocumented/installation-specific log path.
- Direct access to screen coordinates needed for replacement overlay.
- Same core can later serve Quest, Tutorial and UI modules.

### Costs

- OCR errors require normalization, stabilization and confidence gating.
- Dialogue region/layout detection must exclude chat and unrelated UI.
- DPI/resolution support needs deliberate handling.

## Optional future adapter

A `Client.txt` adapter may be added later if a stable source is identified. It may supply area/NPC/event context, but it must remain optional and must not become the primary text source for Dialogue.
