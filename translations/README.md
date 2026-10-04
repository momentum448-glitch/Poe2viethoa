# Translation source data

`dialogue.json` is the human-reviewable source for Story Dialogue translations.

Runtime code does not edit this file. A build step converts it into SQLite:

```bat
.venv\Scripts\python.exe tools\build_translation_db.py
```

## Record shape

```json
{
  "id": "dialogue_example_001",
  "source": "English source text",
  "vi": "Bản dịch tiếng Việt",
  "speaker": "NPC name or null",
  "area": "Area name or null",
  "type": "dialogue",
  "status": "approved",
  "aliases": []
}
```

Allowed status values:

- `draft`
- `reviewed`
- `approved`

Only `reviewed` and `approved` records are used by the normal runtime matcher.

## Current state

The repository intentionally starts with an empty translation corpus. The previously translated Clearfell dataset should be imported only after the local source is recovered and normalized into this schema.

Do not commit extracted raw game corpora merely because they are technically available. Keep engine code, translation work, and raw third-party source assets conceptually separate.
