# Vietnamese translation source

This directory stores **our Vietnamese translation work only**.

Raw English PoE2 dialogue is not committed here. It is reconstructed locally by:

```bat
SOURCE_SYNC.bat
```

That command creates a gitignored source corpus under `source_data/`, then joins it with `dialogue_vi.json` and builds:

```text
runtime/translations.sqlite3
```

## Why source and translation are separated

`dialogue_vi.json` uses stable `source_id` values and does not duplicate the upstream English game corpus.

Benefits:

- raw upstream game text stays outside this public repository;
- source snapshots can be refreshed independently;
- Vietnamese work remains reviewable in Git;
- a source text change naturally produces a new fingerprint/ID that needs review.

## Translation entry

```json
{
  "source_id": "dlg_npctextaudio_0123456789abcdefabcd",
  "vi": "Bản dịch tiếng Việt.",
  "status": "reviewed",
  "review": "ai_alpha_2026-10-04"
}
```

Statuses:

- `draft`: not used by Normal runtime;
- `reviewed`: allowed in Alpha runtime;
- `approved`: human-QC locked translation.

## Fresh-source policy

Do not import the old project dictionary.

Current source snapshots are pinned in `sources/sources.lock.json` and rebuilt through `tools/source_sync.py`.

The initial Alpha Vietnamese entries were recreated from the fresh pinned 2026 source and real OCR evidence, not copied from the previous project corpus.
