import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from sample_data import sample_items

from ignis_wo.contracts import ExtractionOutput
from ignis_wo.extraction.adapters import LiveAdapter, ReplayAdapter, ReplayMiss, gold_item_to_output
from ignis_wo.extraction.project import project
from ignis_wo.extraction.validate import validate_output

VALID = {
    "entities": [
        {"id": "e0", "type": "PhysicalObject/DrivingObject", "start": 0, "end": 4, "text": "pump"},
        {"id": "e1", "type": "Property/UndesirableProperty", "start": 5, "end": 10, "text": "noisy"},
    ],
    "relations": [{"head": "e1", "tail": "e0", "type": "hasParticipant/hasPatient"}],
}


def with_change(path: list, value) -> dict:
    output = json.loads(json.dumps(VALID))
    target = output
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return output


class OffsetTests(unittest.TestCase):
    def test_multi_token_span_converts_to_characters(self):
        item = sample_items()[6]
        text_norm, output = gold_item_to_output(item)
        belt = output["entities"][1]
        self.assertEqual(text_norm[belt["start"]:belt["end"]], "conveyor belt")

    def test_single_token_record_and_final_token(self):
        item = {"tokens": ["leaking"], "entities": [{"start": 0, "end": 1, "type": "Process/UndesirableProcess"}], "relations": []}
        text_norm, output = gold_item_to_output(item)
        self.assertEqual(output["entities"][0], {"id": "e0", "type": "Process/UndesirableProcess", "start": 0, "end": 7, "text": "leaking"})
        self.assertEqual(text_norm, "leaking")


class ValidatorTests(unittest.TestCase):
    def assert_rejected(self, output, fragment: str):
        validated, errors = validate_output(output, "pump noisy")
        self.assertIsNone(validated)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_valid_output_passes(self):
        validated, errors = validate_output(VALID, "pump noisy")
        self.assertEqual(errors, [])
        self.assertIsInstance(validated, ExtractionOutput)

    def test_unknown_label(self):
        self.assert_rejected(with_change(["entities", 0, "type"], "PhysicalObject/Spaceship"), "unknown label")

    def test_offsets_out_of_bounds(self):
        self.assert_rejected(with_change(["entities", 1, "end"], 99), "out of bounds")

    def test_span_text_mismatch(self):
        self.assert_rejected(with_change(["entities", 0, "text"], "pomp"), "does not match")

    def test_missing_relation_entity(self):
        self.assert_rejected(with_change(["relations", 0, "head"], "e9"), "missing entity")

    def test_unknown_relation_type(self):
        self.assert_rejected(with_change(["relations", 0, "type"], "causes"), "unknown type")

    def test_schema_violation(self):
        self.assert_rejected("not json", "schema")


class AdapterTests(unittest.TestCase):
    def test_replay_miss_is_a_hard_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay.jsonl"
            path.write_text("", encoding="utf-8")
            adapter = ReplayAdapter(path, "maintie-lora", "v1")
            with self.assertRaises(ReplayMiss):
                adapter.extract("pump noisy")

    def test_live_adapter_sends_json_schema_and_records_replay(self):
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                received.update(json.loads(self.rfile.read(length)))
                reply = {"choices": [{"message": {"content": json.dumps(VALID)}}]}
                body = json.dumps(reply).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *arguments):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                record_path = Path(directory) / "replay.jsonl"
                base_url = f"http://127.0.0.1:{server.server_port}/v1"
                live = LiveAdapter(base_url, "maintie-lora", "v1", record_path=record_path)
                self.assertEqual(live.extract("pump noisy"), VALID)
                replay = ReplayAdapter(record_path, "maintie-lora", "v1")
                self.assertEqual(replay.extract("pump noisy"), VALID)
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(received["model"], "maintie-lora")
        self.assertEqual(received["temperature"], 0)
        self.assertEqual(received["response_format"]["type"], "json_schema")


class ProjectionTests(unittest.TestCase):
    def project_item(self, index: int):
        text_norm, output = gold_item_to_output(sample_items()[index])
        validated, errors = validate_output(output, text_norm)
        self.assertEqual(errors, [])
        return project(f"r{index}", validated)

    def test_fault_follows_relation_to_its_component(self):
        projection = self.project_item(0)
        self.assertEqual([(fault.component, fault.fault_class) for fault in projection.faults], [("seal", "Process/UndesirableProcess")])
        self.assertEqual(projection.components, ["pump", "seal"])

    def test_fault_without_relation_attaches_to_the_only_component(self):
        projection = self.project_item(4)
        self.assertEqual(projection.faults[0].component, "pump")

    def test_fault_without_relation_and_two_components_is_unattributed(self):
        projection = self.project_item(3)
        self.assertIsNone(projection.faults[0].component)

    def test_actions_are_activity_classes(self):
        projection = self.project_item(1)
        self.assertEqual(projection.actions, ["Activity/MaintenanceActivity/Replace"])


if __name__ == "__main__":
    unittest.main()
