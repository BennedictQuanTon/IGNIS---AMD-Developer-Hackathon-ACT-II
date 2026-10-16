import json
import tempfile
import unittest
from pathlib import Path

from mock_chat_server import ScriptedServer, chat_reply, reply
from sample_data import build_sample_records, sample_items

from ignis_wo.__main__ import main
from ignis_wo.contracts import ExtractionOutput
from ignis_wo.evaluation.scorer import score_items
from ignis_wo.extraction.adapters import LiveAdapter, ReplayAdapter, ReplayMiss, gold_item_to_output, token_spans_to_output
from ignis_wo.extraction.project import project
from ignis_wo.extraction.suggest import suggest
from ignis_wo.extraction.validate import validate_output
from ignis_wo.hosted.transport import ChatClient, ProviderError

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

    def test_live_adapter_converts_token_spans_and_records_replay(self):
        token_form = {"entities": [{"id": "e0", "type": "PhysicalObject/DrivingObject", "start_token": 0, "end_token": 1, "text": "pump"},
                                   {"id": "e1", "type": "Property/UndesirableProperty", "start_token": 1, "end_token": 2, "text": "noisy"}],
                      "relations": [{"head": "e1", "tail": "e0", "type": "hasParticipant/hasPatient"}]}
        with tempfile.TemporaryDirectory() as directory, ScriptedServer([reply(chat_reply(json.dumps(token_form)))]) as server:
            record_path = Path(directory) / "replay.jsonl"
            live = LiveAdapter(ChatClient(server.base_url, "rc-secret"), "DeepSeek-V4-Flash", record_path=record_path)
            self.assertEqual(live.extract("pump noisy"), VALID)
            replay = ReplayAdapter(record_path, "DeepSeek-V4-Flash", live.model_version)
            self.assertEqual(replay.extract("pump noisy"), VALID)
            recorded = record_path.read_text(encoding="utf-8")
        body = server.requests[0]["body"]
        self.assertEqual(body["model"], "DeepSeek-V4-Flash")
        self.assertEqual(body["temperature"], 0)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertIn("[0] pump [1] noisy", body["messages"][-1]["content"])
        self.assertTrue(live.model_version.startswith("extraction-instruction-v1-"))
        self.assertNotIn("rc-secret", recorded)

    def test_live_adapter_sends_the_token_schema_in_json_schema_mode(self):
        with ScriptedServer([reply(chat_reply('{"entities": [], "relations": []}'))]) as server:
            live = LiveAdapter(ChatClient(server.base_url), "MiMo-V2.6-Flash", output_mode="json_schema")
            self.assertEqual(live.extract("pump noisy"), {"entities": [], "relations": []})
        schema = server.requests[0]["body"]["response_format"]["json_schema"]["schema"]
        self.assertIn("start_token", schema["properties"]["entities"]["items"]["properties"])


class LiveFailureTests(unittest.TestCase):
    def test_a_wrongly_shaped_answer_fails_only_that_record(self):
        with ScriptedServer([reply(chat_reply('{"entities": 3}'))]) as server:
            live = LiveAdapter(ChatClient(server.base_url), "DeepSeek-V4-Flash")
            suggestion = suggest(build_sample_records()[0], live)
        self.assertEqual(suggestion.status, "failed_terminal")
        self.assertTrue(suggestion.errors[0].startswith("provider_error: invalid_response"))

    def test_a_record_that_failed_live_replays_as_the_same_failure(self):
        record = build_sample_records()[0]
        with tempfile.TemporaryDirectory() as directory, ScriptedServer([reply(chat_reply("not json"))]) as server:
            record_path = Path(directory) / "replay.jsonl"
            live = LiveAdapter(ChatClient(server.base_url), "DeepSeek-V4-Flash", record_path=record_path)
            live_suggestion = suggest(record, live)
            replayed = suggest(record, ReplayAdapter(record_path, "DeepSeek-V4-Flash", live.model_version))
        self.assertEqual((replayed.status, replayed.suggestion_id), ("failed_terminal", live_suggestion.suggestion_id))
        self.assertTrue(replayed.errors[0].startswith("provider_error: invalid_response: replayed"))


class TokenSpanTests(unittest.TestCase):
    def test_multi_token_span_is_end_exclusive(self):
        raw = {"entities": [{"id": "e0", "type": "PhysicalObject", "start_token": 1, "end_token": 3, "text": "conveyor belt"}]}
        output, reanchored = token_spans_to_output(raw, "check conveyor belt tension")
        self.assertEqual((output["entities"][0]["start"], output["entities"][0]["end"], reanchored), (6, 19, 0))

    def test_off_by_one_indices_are_reanchored_on_the_echoed_text(self):
        raw = {"entities": [{"id": "e0", "type": "PhysicalObject", "start_token": 0, "end_token": 1, "text": "depth counter"},
                            {"id": "e1", "type": "State", "start_token": False, "end_token": 1, "text": "unserviceable"}]}
        output, reanchored = token_spans_to_output(raw, "depth counter unserviceable")
        self.assertEqual([(entity["start"], entity["end"]) for entity in output["entities"]], [(0, 13), (14, 27)])
        self.assertEqual(reanchored, 2)

    def test_repeated_text_anchors_nearest_the_declared_index(self):
        raw = {"entities": [{"id": "e0", "type": "PhysicalObject", "start_token": 3, "end_token": 5, "text": "pump"}]}
        output, _ = token_spans_to_output(raw, "pump seal and pump leak")
        self.assertEqual(output["entities"][0]["start"], 14)

    def test_out_of_range_span_is_rejected_by_the_validator_not_raised(self):
        raw = {"entities": [{"id": "e0", "type": "PhysicalObject/DrivingObject", "start_token": 1, "end_token": 5, "text": "motor"}], "relations": []}
        output, _ = token_spans_to_output(raw, "pump noisy")
        validated, errors = validate_output(output, "pump noisy")
        self.assertIsNone(validated)
        self.assertTrue(any("out of bounds" in error for error in errors), errors)

    def test_echoed_text_absent_from_the_source_is_rejected(self):
        raw = {"entities": [{"id": "e0", "type": "PhysicalObject/DrivingObject", "start_token": 1, "end_token": 2, "text": "motor"}], "relations": []}
        validated, errors = validate_output(token_spans_to_output(raw, "pump noisy")[0], "pump noisy")
        self.assertIsNone(validated)
        self.assertTrue(any("does not match" in error for error in errors), errors)


class FailingAdapter:
    mode = "live"
    model_id = "m"
    model_version = "v"

    def __init__(self, kind):
        self.kind = kind

    def extract(self, text_norm):
        raise ProviderError(self.kind, "scripted failure")


class SuggestFailureTests(unittest.TestCase):
    def record(self):
        return build_sample_records()[0]

    def test_a_bad_answer_fails_only_that_record(self):
        suggestion = suggest(self.record(), FailingAdapter("truncated"))
        self.assertEqual(suggestion.status, "failed_terminal")
        self.assertTrue(suggestion.errors[0].startswith("provider_error: truncated"))

    def test_rate_limits_outages_and_auth_raise_so_the_stage_can_be_retried(self):
        for kind in ("rate_limited", "unavailable", "timeout", "auth", "credits"):
            with self.assertRaises(ProviderError):
                suggest(self.record(), FailingAdapter(kind))


class ScorerFailureTests(unittest.TestCase):
    def test_outages_raise_instead_of_scoring_as_empty(self):
        for kind in ("rate_limited", "unavailable", "timeout", "bad_request"):
            with self.assertRaises(ProviderError):
                score_items(sample_items(), FailingAdapter(kind))

    def test_bad_answers_count_as_empty_predictions(self):
        result = score_items(sample_items(), FailingAdapter("invalid_response"))
        self.assertEqual(result["provider_failures"], {"invalid_response": len(sample_items())})
        self.assertEqual(result["entities"]["correct"], 0)


class EvalLedgerTests(unittest.TestCase):
    def run_final(self, directory: Path, model_id: str):
        replay = directory / "replay.jsonl"
        replay.write_text("", encoding="utf-8")
        main(["eval", "--split", "test", "--final", "--mode", "replay", "--replay", str(replay), "--model-id", model_id,
              "--model-version", "v", "--ledger", str(directory / "ledger.jsonl"), "--gold", str(directory / "none.json")])

    def test_a_scored_model_is_refused_but_another_model_is_not(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            ledger.write_text(json.dumps({"model_id": "a", "model_version": "v"}) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "refused"):
                self.run_final(Path(directory), "a")
            with self.assertRaises(FileNotFoundError):
                self.run_final(Path(directory), "b")

    def test_replay_without_a_model_id_is_refused(self):
        with self.assertRaisesRegex(SystemExit, "replay mode needs"):
            main(["eval", "--mode", "replay", "--replay", "unused.jsonl", "--model-id", ""])


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
