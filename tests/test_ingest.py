import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from ignis_wo.ingest.mapping import build_records, confirm_mapping, propose_mapping
from ignis_wo.ingest.registry import parse_file

HEADER = ["WO #", "Work Order Description", "Reported Date", "Downtime (h)"]
ROWS = [["WO-1", "pump seal leaking", "2025-02-01", "2.5"], ["WO-2", "hose  worn", "2025-02-03", "1"]]


def write_inputs(directory: Path) -> list[Path]:
    objects = [dict(zip(HEADER, row)) for row in ROWS]
    csv_path = directory / "export.csv"
    csv_path.write_text("\n".join(",".join(row) for row in [HEADER] + ROWS) + "\n", encoding="utf-8")
    tsv_path = directory / "export.tsv"
    tsv_path.write_text("\n".join("\t".join(row) for row in [HEADER] + ROWS) + "\n", encoding="utf-8")
    json_path = directory / "export.json"
    json_path.write_text(json.dumps(objects), encoding="utf-8")
    jsonl_path = directory / "export.jsonl"
    jsonl_path.write_text("\n".join(json.dumps(item) for item in objects), encoding="utf-8")
    workbook = Workbook()
    workbook.active.append(HEADER)
    for row in ROWS:
        workbook.active.append(row)
    xlsx_path = directory / "export.xlsx"
    workbook.save(xlsx_path)
    return [csv_path, tsv_path, json_path, jsonl_path, xlsx_path]


def records_from(path: Path):
    source_file, rows = parse_file(path)
    proposal = propose_mapping(sorted(rows[0].values))
    revision = confirm_mapping(proposal, "tester", "test")
    return build_records(source_file, rows, revision)


class IngestTests(unittest.TestCase):
    def test_every_format_yields_the_same_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in write_inputs(Path(directory)):
                records, issues = records_from(path)
                fields = [(record.text_norm, record.event_date, record.downtime_hours) for record in records]
                self.assertEqual(issues, [], path.suffix)
                self.assertEqual(fields, [("pump seal leaking", "2025-02-01", 2.5), ("hose worn", "2025-02-03", 1.0)])

    def test_proposal_maps_known_headers(self):
        proposal = propose_mapping(HEADER)
        self.assertEqual(proposal.mapping["text"], "Work Order Description")
        self.assertEqual(proposal.mapping["downtime_hours"], "Downtime (h)")
        self.assertIsNone(proposal.mapping["asset_id"])

    def test_missing_optional_columns_stay_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "minimal.csv"
            path.write_text("Description\npump noisy\n", encoding="utf-8")
            records, _ = records_from(path)
        self.assertIsNone(records[0].event_date)
        self.assertIsNone(records[0].asset_id)
        self.assertIsNone(records[0].downtime_hours)

    def test_mapping_without_text_column_is_refused(self):
        proposal = propose_mapping(["Equipment ID", "Reported Date"])
        with self.assertRaises(ValueError):
            confirm_mapping(proposal, "tester", "test")

    def test_bad_rows_are_reported_with_their_location(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("Description,Downtime\n,1\npump noisy,abc\n", encoding="utf-8")
            records, issues = records_from(path)
        self.assertEqual(len(records), 1)
        self.assertIsNone(records[0].downtime_hours)
        self.assertEqual(issues, ["row 2: rejected, empty text", "row 3: downtime is not a number, left empty", "row 3: event date missing"])

    def test_record_ids_are_stable_across_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_inputs(Path(directory))[0]
            first, _ = records_from(path)
            second, _ = records_from(path)
        self.assertEqual([record.record_id for record in first], [record.record_id for record in second])

    def test_negative_nan_and_infinite_downtime_are_exposed_and_not_computed(self):
        from ignis_wo.ingest.mapping import build_records, confirm_mapping, propose_mapping
        from ignis_wo.ingest.registry import parse_file

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid-hours.csv"
            path.write_text("WO #,Work Order Description,Downtime (h)\n1,pump noise,-2\n2,pump seal,NaN\n3,pump leak,Infinity\n", encoding="utf-8")
            source, rows = parse_file(path)
            revision = confirm_mapping(propose_mapping(["WO #", "Work Order Description", "Downtime (h)"]), "reviewer", "checked")
            records, issues = build_records(source, rows, revision)
            self.assertEqual([record.downtime_hours for record in records], [None, None, None])
            self.assertEqual(sum("must be finite and nonnegative" in issue for issue in issues), 3)


if __name__ == "__main__":
    unittest.main()
