import json
import tempfile
import unittest
from pathlib import Path

from sample_data import sample_adapter, sample_items, write_sample_csv

from ignis_wo.artifacts import StageFailed
from ignis_wo.extraction.adapters import FixtureAdapter
from ignis_wo.pipeline import RunOptions, run_pipeline

STAGES = ["01_ingest", "02_mapping", "03_extract", "04_review", "05_snapshot", "06_facts", "07_explain", "08_claims", "09_report"]


def read_manifest(directory: Path) -> list[dict]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    return manifest["stages"]


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)
        self.export = write_sample_csv(self.path / "export.csv")

    def tearDown(self):
        self.directory.cleanup()

    def run_into(self, name: str, adapter=None) -> dict:
        options = RunOptions(self.export, self.path / name, adapter or sample_adapter(), synthetic=True,
                             confirm_mapping=True, demo_auto_review=True)
        return run_pipeline(options)

    def test_every_stage_succeeds_and_is_reproducible(self):
        first = self.run_into("first")
        second = self.run_into("second")
        first_stages = read_manifest(self.path / "first")
        second_stages = read_manifest(self.path / "second")
        self.assertEqual([entry["stage"] for entry in first_stages], STAGES)
        self.assertEqual(
            [entry["output_hash"] for entry in first_stages if entry["stage"] != "04_review"],
            [entry["output_hash"] for entry in second_stages if entry["stage"] != "04_review"],
        )
        self.assertEqual(first["pdf_sha256"], second["pdf_sha256"])
        self.assertEqual(first["records"], 8)

    def test_outputs_are_a_pdf_and_a_board(self):
        self.run_into("run")
        pdf = (self.path / "run" / "report.pdf").read_bytes()
        board = (self.path / "run" / "board.html").read_text(encoding="utf-8")
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn("SYNTHETIC DATA / AUTO-REVIEW DEMO / FIXTURE MODE", board)
        self.assertIn("hose has triage priority 12 (Medium)", board)

    def test_corrupt_model_output_stops_at_the_extraction_stage(self):
        items = sample_items()
        items[2]["entities"][1]["type"] = "State/Invented"
        with self.assertRaises(StageFailed) as raised:
            self.run_into("corrupt", FixtureAdapter(items, model_version="corrupt"))
        self.assertEqual(raised.exception.stage, "03_extract")
        stages = read_manifest(self.path / "corrupt")
        self.assertEqual(stages[-1]["stage"], "03_extract")
        self.assertEqual(stages[-1]["status"], "failed")
        self.assertIn("unknown label", stages[-1]["errors"][0])
        self.assertFalse((self.path / "corrupt" / "report.pdf").exists())

    def test_normal_source_run_requires_explicit_mapping_and_record_decisions(self):
        options = RunOptions(self.export, self.path / "gated", sample_adapter(), synthetic=True)
        with self.assertRaises(StageFailed) as mapping_failure:
            run_pipeline(options)
        self.assertEqual(mapping_failure.exception.stage, "02_mapping")
        self.assertFalse((self.path / "gated" / "report.pdf").exists())

        options.confirm_mapping = True
        with self.assertRaises(StageFailed) as review_failure:
            run_pipeline(options)
        self.assertEqual(review_failure.exception.stage, "05_snapshot")
        review = json.loads((self.path / "gated" / "04_review.json").read_text(encoding="utf-8"))
        self.assertEqual(review, [])

    def test_demo_auto_review_cannot_approve_source_data_or_reuse_report_directory(self):
        invalid = RunOptions(self.export, self.path / "invalid-demo", sample_adapter(), synthetic=False, confirm_mapping=True, demo_auto_review=True)
        with self.assertRaises(StageFailed) as raised:
            run_pipeline(invalid)
        self.assertEqual(raised.exception.stage, "04_review")

        result = self.run_into("published")
        original_pdf = (self.path / "published" / "report.pdf").read_bytes()
        with self.assertRaises(ValueError):
            self.run_into("published")
        self.assertEqual((self.path / "published" / "report.pdf").read_bytes(), original_pdf)


if __name__ == "__main__":
    unittest.main()
