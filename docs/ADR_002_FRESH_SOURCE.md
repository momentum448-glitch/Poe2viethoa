# ADR-002 — Fresh Dialogue Source Corpus

**Status:** Accepted / Locked  
**Date:** 2026-10-04

## Decision

The project must not depend on:

- the previous `Translate PJ` dictionary;
- the old 208-line Clearfell corpus;
- Remote Desktop for source recovery.

Story Dialogue source is rebuilt locally from pinned, reproducible 2026 public source snapshots.

## Sources

### Primary English source

`addohm/poe2-en-cn-dict`

Pinned ref:

```text
28d683c99600eb407b4e014ccaf8247532fb4607
```

Consumed outputs:

- `NPCTextAudio.json`
- `NPCTalkDialogueTextAudio.json`

Only the English side is used.

This source retains `<continue>` markers, which map naturally to the individual dialogue pages observed by OCR in PoE2.

### Optional context source

`fireMCG/Exiled-Vault`

Pinned ref:

```text
b3dd7457aa4e7f126021b8d8577f38ef205490c7
```

Used locally to enrich exact transcript matches with:

- speaker;
- topic;
- transcript validation.

The context source is optional. Failure to download it must not prevent the English corpus from building.

## Repository boundary

Raw upstream/game text must not be committed to this repository.

```text
upstream snapshots
      ↓
source_data/          # gitignored
      ↓
dialogue_corpus.jsonl # gitignored
      +
translations/dialogue_vi.json
      ↓
runtime/translations.sqlite3 # gitignored
```

The committed Vietnamese file contains only project-created translation work keyed by deterministic `source_id`.

## Source IDs

A displayed segment is normalized and fingerprinted with SHA-256.

Current form:

```text
dlg_<source_table>_<first 20 hex chars of fingerprint>
```

This deliberately treats meaningful English source changes as new translation work rather than silently reusing a possibly stale translation.

## Validation

The nine unique Renly/Una dialogue segments captured in the passing Phase 1 real-game QC were checked against the pinned 2026 English source.

All nine were present, including their `<continue>` page boundaries.

An older 2025 public dump truncated one Una record, while the pinned 2026 source retained the full sentence. This is direct evidence for using the fresh-source workflow rather than older data.

## Distribution note

Source syncing is a local build step. Before distributing a large compiled translation corpus publicly, re-check current GGG terms and upstream data licensing.
