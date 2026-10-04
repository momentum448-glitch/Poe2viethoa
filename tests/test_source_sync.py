import unittest

from tools.source_sync import build_corpus, normalize_compare


class SourceSyncTests(unittest.TestCase):
    def test_continue_segments_and_context_enrichment(self):
        full = "First sentence. <continue>Second sentence."
        key = normalize_compare(full)
        source_rows = [
            {
                "table": "NPCTextAudio",
                "upstream_index": 10,
                "upstream_id": None,
                "full_text": full,
                "compare_key": key,
            }
        ]
        context_index = {
            key: [
                {
                    "speaker": "Renly",
                    "topic": "Example",
                    "text": "First sentence. Second sentence.",
                    "compare_key": key,
                    "vault_path": "R/Renly/Renly.md",
                }
            ]
        }

        corpus, stats = build_corpus(
            source_rows,
            context_index,
            source_ref="source-ref",
            context_ref="context-ref",
        )

        self.assertEqual(len(corpus), 2)
        self.assertEqual(corpus[0]["source"], "First sentence.")
        self.assertEqual(corpus[1]["source"], "Second sentence.")
        self.assertEqual(corpus[0]["speaker"], "Renly")
        self.assertEqual(corpus[0]["topic"], "Example")
        self.assertEqual(stats["context_exact_rows"], 1)
        self.assertEqual(stats["with_speaker"], 2)

    def test_source_id_is_deterministic_for_same_segment(self):
        source_rows = [
            {
                "table": "NPCTextAudio",
                "upstream_index": 1,
                "upstream_id": None,
                "full_text": "Same visible line.",
                "compare_key": normalize_compare("Same visible line."),
            },
            {
                "table": "NPCTextAudio",
                "upstream_index": 2,
                "upstream_id": None,
                "full_text": "Same visible line.",
                "compare_key": normalize_compare("Same visible line."),
            },
        ]

        corpus, _ = build_corpus(
            source_rows,
            {},
            source_ref="source-ref",
            context_ref="context-ref",
        )

        self.assertEqual(len(corpus), 1)
        self.assertTrue(corpus[0]["source_id"].startswith("dlg_npctextaudio_"))


if __name__ == "__main__":
    unittest.main()
