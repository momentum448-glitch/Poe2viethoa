# Translation Factory — first milestone

Build: `0.5.0-alpha.1 / factory-20261004-01`.

The first milestone turns verified untranslated NPC pages into source-bound
Vietnamese drafts, reviewed catalog entries and an offline runtime. The first
batch adds seven Una/Renly pages to the nine-record Alpha baseline.

## Data and review states

`translations/glossary.json` defines project style and terms. Proper names keep
their in-game spelling; NPCs use tôi/bạn. It is a project glossary, not an official
Vietnamese localization reference.

`translations/batches/*.json` stores Vietnamese work, source IDs/hashes, context,
draft/review notes and the active catalog record's digest. English game transcripts
remain in ignored `source_data/`. Prompt/review packets go to ignored `factory_reports/`.

| State | Meaning | Runtime publication |
| --- | --- | --- |
| draft | Proposed text requiring semantic review | Rejected |
| reviewed | Explicit AI/author review with source/context and passing QA | Allowed in Alpha |
| approved | Reviewed text with a recorded user QC result | Allowed; protected against downgrade |

Automatic QA does not judge every meaning or tone. The author must read complete
source pages and neighboring pages before marking reviewed. The AI drafting step
currently runs in chat from the local bundle; a bulk API translation client is not
part of this milestone. Reviewed translation memory supplies same-speaker references;
similar text never automatically becomes the translation of a different page.

## Operator workflow

Run commands from the repository root using the installed Python environment.
On Windows the prefix is `.venv\Scripts\python.exe -X utf8 -m`.
The examples use `python -X utf8 -m` for readability.

1. Sync the pinned English corpus with `SOURCE_SYNC.bat` if it is absent/stale.
   Snapshot changes require fresh batches/review; the factory validates the actual
   corpus snapshot as well as the lock-file fingerprint.
2. Select only exact fresh-source MISS pages from a user QC ZIP:

   ```bat
   python -X utf8 -m tools.translation_factory prepare --batch-id my-batch --from-qc path-to-QC.zip --output translations/batches/my-batch.json
   ```

   Repeat `--source-id ID` instead for explicit page selection or revision of an
   existing translation. An existing batch file is never overwritten. Unresolved
   or ambiguous OCR events are reported for manual inspection; fuzzy chat is excluded.
3. Export a local source/context/glossary/TM bundle:

   ```bat
   python -X utf8 -m tools.translation_factory bundle --batch translations/batches/my-batch.json --output factory_reports/my-batch.md
   ```

   The author reads it, fills `vi` and adds draft notes in the JSON. Keep the IDs,
   hashes and page metadata from prepare. Preserve all meaning, relationships and
   uncertainty; review against the entire source rather than a partial OCR fragment.
4. Validate the proposed text:

   ```bat
   python -X utf8 -m tools.translation_factory qa --batch translations/batches/my-batch.json
   ```

   QA checks nonempty text, names, literal numbers/placeholders, markup, duplicate
   IDs, source/context drift and editing after review. Errors block the next step;
   length warnings require the author's attention. Return codes: 0 pass, 1 QA
   errors, 2 command/input failure. Empty prepared drafts are expected to fail QA.
5. After explicit semantic review, record the reviewer and notes:

   ```bat
   python -X utf8 -m tools.translation_factory mark-reviewed --batch translations/batches/my-batch.json --reviewer AI_or_author --note "Source/context reviewed; describe decisions."
   python -X utf8 -m tools.translation_factory publish --batch translations/batches/my-batch.json
   ```

   This atomically merges the reviewed entries into `translations/dialogue_vi.json`.
   Unrelated reviewed records remain intact; a conflicting edit made while the batch
   was being reviewed blocks publication. Repeating publication of unchanged content
   is idempotent. Operator writes are sequential; parallel catalog editing is not supported.
6. Rebuild using `SETUP_ALPHA.bat` or `python -X utf8 -m tools.build_translation_db`.
   Invalid hashes, malformed/duplicate entries and build failure preserve the previous
   runtime DB. `RUN_ALPHA.bat` detects changed catalog data and prepares it automatically.
7. The user runs panel **QC 60 giây**, reads the new pages and reports any wording,
   clipping or font-size issues. The current panel still produces `QC_PHASE4_RESULT_*.zip`.
   Once the user has passed those texts, record the human QC and republish:

   ```bat
   python -X utf8 -m tools.translation_factory approve --batch translations/batches/my-batch.json --reviewer user_QC --note "User confirmed the new pages in build X/session Y."
   python -X utf8 -m tools.translation_factory publish --batch translations/batches/my-batch.json
   ```

   Approval can promote the already published reviewed batch. Changing approved
   content requires a new revision batch and a new approval; old approval is not reused.

## First release checkpoint

Batch `qc-alpha3-20261004-01` is AI-reviewed, QA passes with 0 errors/warnings,
and the runtime contains 16 records. The nine baseline records remain intact.
All 102 tests pass, including real CLI exit-state checks, publication conflict/
rollback, review tampering, human promotion and old-runtime preservation.

Replaying three prior QC logs keeps all 22 prior High overlay decisions on their
existing IDs. In Alpha.3 QC, all 15 emitted pages now match exactly, including
the seven previously untranslated pages. This is matcher/build validation; new
Vietnamese rendering and final language acceptance still need the user's game QC.

User pages: Una → Introduction / Renly (3 new pages), Renly → Fatherhood (4 pages).
Hold each page 3–4 seconds, exercise Inventory, and check one existing Renly
Introduction page. Send the panel QC ZIP and any wording feedback. Subsequent
batches should prioritize exact MISS pages observed in actual play.
