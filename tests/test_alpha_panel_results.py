from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from app.alpha_app import AlphaApp


class PanelResultRestoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.panel = AlphaApp.__new__(AlphaApp)
        self.panel.root = self.root
        self.panel.archive = None
        self.panel.file_label = Mock()
        self.panel.open_button = Mock()
        self.panel.pin_button = Mock()

    def test_restore_finds_new_results_directory_from_old_absolute_pointer(self):
        (self.root / "results").mkdir()
        path = self.root / "results/QC_PHASE4_RESULT_previous.zip"
        path.write_bytes(b"test")
        (self.root / "LAST_QC_RESULT.txt").write_text(f"FILE:\nC:\\old-install\\{path.name}\n")
        self.panel.restore_result()
        self.assertEqual(self.panel.archive, path)
        self.panel.pin_button.configure.assert_called_with(state="normal")

    def test_restore_still_supports_legacy_root_result(self):
        path = self.root / "ALPHA_RESULT_previous.zip"
        path.write_bytes(b"test")
        (self.root / "LAST_ALPHA_RESULT.txt").write_text(str(path))
        self.panel.restore_result()
        self.assertEqual(self.panel.archive, path)

    def test_restore_never_follows_a_result_symlink_outside_installation(self):
        external = self.root / "external.zip"
        external.write_bytes(b"unique")
        name = "QC_PHASE4_RESULT_symlink.zip"
        (self.root / name).symlink_to(external)
        (self.root / "LAST_QC_RESULT.txt").write_text(name)
        self.panel.restore_result()
        self.assertIsNone(self.panel.archive)


if __name__ == "__main__":
    unittest.main()
