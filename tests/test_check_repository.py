import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.check_repository as checker


class MarkdownLinkChecks(unittest.TestCase):
    def test_valid_relative_absolute_and_external_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            page = root / "README.md"
            page.write_text("[page](docs/page.md) [root](/README.md) [external](https://example.test/missing.md) [anchor](#part)", encoding="utf-8")
            (root / "docs" / "page.md").write_text("ok", encoding="utf-8")
            with patch.object(checker, "ROOT", root), patch.object(checker, "markdown_files", return_value=[page]):
                self.assertEqual(checker.check_markdown_links(), [])

    def test_missing_target_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "README.md"
            page.write_text("[missing](absent.md)", encoding="utf-8")
            with patch.object(checker, "ROOT", root), patch.object(checker, "markdown_files", return_value=[page]):
                self.assertIn("missing link target", checker.check_markdown_links()[0])

    def test_links_inside_fenced_examples_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "README.md"
            page.write_text("```md\n[example](not-real.md)\n```\n", encoding="utf-8")
            with patch.object(checker, "ROOT", root), patch.object(checker, "markdown_files", return_value=[page]):
                self.assertEqual(checker.check_markdown_links(), [])

    def test_target_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "README.md"
            page.write_text("[outside](../outside.md)", encoding="utf-8")
            with patch.object(checker, "ROOT", root), patch.object(checker, "markdown_files", return_value=[page]):
                self.assertIn("escapes repository", checker.check_markdown_links()[0])

    def test_ignored_environment_and_data_directories_are_not_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = root / ".venv" / "Lib" / "site-packages" / "sample"
            data = root / "datasets"
            env.mkdir(parents=True)
            data.mkdir()
            (env / "README.md").write_text("[missing](third-party-file.md)", encoding="utf-8")
            (env / "broken.yml").write_text("this: [is: invalid", encoding="utf-8")
            (data / "broken.json").write_text("{not json", encoding="utf-8")
            with patch.object(checker, "ROOT", root):
                self.assertEqual(checker.check_markdown_links(), [])
                self.assertEqual(checker.check_configuration(), [])


if __name__ == "__main__":
    unittest.main()
