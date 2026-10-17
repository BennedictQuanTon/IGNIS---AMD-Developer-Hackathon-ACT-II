import json
import tempfile
import unittest
from pathlib import Path

from mock_chat_server import ScriptedServer, chat_reply, reply
from sample_data import sample_items

from ignis_wo.evaluation.benchmark import (
    already_scored,
    extraction_call,
    extraction_cases,
    extraction_scores,
    ledger_contains,
    percentile,
    run_cases,
    run_complete,
    summarize,
    write_results,
)
from ignis_wo.extraction.adapters import LiveAdapter
from ignis_wo.hosted.capabilities import capability_matrix, probe_plan
from ignis_wo.hosted.prompts import ExtractionPrompt, gold_to_token_form, select_examples
from ignis_wo.hosted.transport import ChatClient, ProviderError


class RunnerTests(unittest.TestCase):
    def test_percentile_uses_nearest_rank(self):
        values = [0.4, 0.1, 0.3, 0.2]
        self.assertEqual(percentile(values, 50), 0.2)
        self.assertEqual(percentile(values, 95), 0.4)
        self.assertIsNone(percentile([], 50))

    def test_credit_exhaustion_stops_the_remaining_cases(self):
        outcomes = iter(["valid", "credits", "valid"])

        def call(case):
            outcome = next(outcomes)
            if outcome == "credits":
                raise ProviderError("credits", "daily usage limit exceeded")
            return {"status": outcome, "attempts": 2, "usage": {"prompt_tokens": 4, "completion_tokens": 3}}

        cases = [{"case_id": f"c{index}"} for index in range(3)]
        rows, _ = run_cases(cases, call)
        self.assertEqual([row["status"] for row in rows], ["valid", "credits", "skipped"])
        summary = summarize(rows, wall_seconds=30)
        self.assertEqual(summary["attempted"], 2)
        self.assertEqual(summary["skipped"], 1)
        self.assertEqual(summary["outcomes"], {"credits": 1, "valid": 1})
        self.assertEqual(summary["retries"], 1)
        self.assertEqual(summary["attempted_per_minute"], 4.0)
        self.assertEqual(summary["valid_per_minute"], 2.0)
        self.assertEqual(summary["prompt_tokens"], 4)

    def test_a_rejected_budget_stops_the_remaining_cases(self):
        def call(case):
            raise ProviderError("budget_rejected", "max_tokens exceeds the maximum output tokens allowed")

        rows, _ = run_cases([{"case_id": "a"}, {"case_id": "b"}], call)
        self.assertEqual([row["status"] for row in rows], ["budget_rejected", "skipped"])

    def test_the_committed_scored_entry_refuses_the_test_split_without_a_local_ledger(self):
        prompt = ExtractionPrompt(select_examples(sample_items(), count=2))
        adapter = LiveAdapter(None, "M", prompt, reasoning_effort=None)
        scored = {"model_id": "M", "model_version": adapter.legacy_model_version(), "max_tokens": 4096,
                  "budget_fallback": False}
        missing_ledger = Path(tempfile.gettempdir()) / "no-such-ledger.jsonl"
        self.assertTrue(already_scored(missing_ledger, adapter, scored))
        with_fallback = LiveAdapter(None, "M", prompt, reasoning_effort=None, budget_fallback=True)
        self.assertFalse(already_scored(missing_ledger, with_fallback, scored))
        self.assertFalse(already_scored(missing_ledger, LiveAdapter(None, "N", prompt, reasoning_effort=None), scored))

    def test_a_local_v1_entry_locks_the_same_model_and_budget(self):
        prompt = ExtractionPrompt(select_examples(sample_items(), count=2))
        adapter = LiveAdapter(None, "N", prompt, reasoning_effort=None)
        other_scored = {"model_id": "M", "model_version": "x", "max_tokens": 4096, "budget_fallback": False}
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            ledger.write_text(json.dumps({"model_id": "N", "model_version": adapter.legacy_model_version()}) + "\n",
                              encoding="utf-8")
            self.assertTrue(already_scored(ledger, adapter, other_scored))
            smaller_budget = LiveAdapter(None, "N", prompt, reasoning_effort=None, max_tokens=2048)
            self.assertFalse(already_scored(ledger, smaller_budget, other_scored))

    def test_the_capability_scan_continues_past_a_rejected_budget(self):
        models = [{"id": "Model-A", "json_output": True}, {"id": "Model-B", "json_output": True}]
        rejected = reply({"error": {"message": "The requested max_tokens (1024) exceeds the maximum output tokens "
                                               "allowed for model Model-A (null)"}}, 400)
        script = [reply({"data": models}), rejected, reply(chat_reply('{"status": "ok"}'))]
        with ScriptedServer(script) as server:
            matrix = capability_matrix(ChatClient(server.base_url, "rc-x"))
        self.assertEqual([row["status"] for row in matrix["probes"]], ["budget_rejected", "ok"])

    def test_cases_past_the_time_budget_are_skipped(self):
        ticks = iter([0, 0, 1, 100, 100, 100])
        rows, _ = run_cases([{"case_id": "a"}, {"case_id": "b"}], lambda case: {"status": "valid"},
                            max_duration_seconds=10, clock=lambda: next(ticks))
        self.assertEqual([row["status"] for row in rows], ["valid", "skipped"])

    def test_test_split_ledger_matches_model_and_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            self.assertFalse(ledger_contains(ledger, "m", "v"))
            ledger.write_text(json.dumps({"model_id": "m", "model_version": "v"}) + "\n", encoding="utf-8")
            self.assertTrue(ledger_contains(ledger, "m", "v"))
            self.assertFalse(ledger_contains(ledger, "m", "other-prompt"))
            self.assertFalse(ledger_contains(ledger, "other-model", "v"))

    def test_an_incomplete_test_run_is_logged_but_does_not_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            ledger.write_text(json.dumps({"model_id": "m", "model_version": "v", "complete": False}) + "\n",
                              encoding="utf-8")
            self.assertFalse(ledger_contains(ledger, "m", "v"))
        complete = {"skipped": 0, "outcomes": {"valid": 3, "invalid": 1, "truncated": 1}}
        self.assertTrue(run_complete(complete))
        self.assertFalse(run_complete({**complete, "skipped": 1}))
        self.assertFalse(run_complete({**complete, "outcomes": {"valid": 3, "rate_limited": 1}}))

    def test_an_unexpected_exception_fails_one_case_and_keeps_the_rest(self):
        def call(case):
            if case["case_id"] == "b":
                raise TypeError("'int' object is not iterable")
            return {"status": "valid"}

        rows, _ = run_cases([{"case_id": "a"}, {"case_id": "b"}, {"case_id": "c"}], call)
        self.assertEqual([row["status"] for row in rows], ["valid", "error", "valid"])
        self.assertIn("TypeError", rows[1]["error"])


class ExtractionBenchmarkTests(unittest.TestCase):
    def test_gold_answers_from_the_mock_score_perfectly_and_write_results(self):
        items = sample_items()[:3]
        script = [reply(chat_reply(json.dumps(gold_to_token_form(item))), headers={"X-RateLimit-Remaining-User-RPM": "9"})
                  for item in items]
        with ScriptedServer(script) as server:
            adapter = LiveAdapter(ChatClient(server.base_url, "rc-x"), "DeepSeek-V4-Flash")
            cases = extraction_cases(items)
            rows, wall_seconds = run_cases(cases, extraction_call(adapter))
        self.assertEqual([row["status"] for row in rows], ["valid"] * 3)
        scores = extraction_scores(cases, rows)
        self.assertEqual(scores["entities"]["f1"], 1.0)
        self.assertEqual(scores["relations"]["f1"], 1.0)
        summary = summarize(rows, wall_seconds)
        self.assertEqual(summary["last_rate_headers"], {"x-ratelimit-remaining-user-rpm": "9"})
        with tempfile.TemporaryDirectory() as directory:
            write_results(Path(directory), rows, summary)
            self.assertEqual(len((Path(directory) / "requests.jsonl").read_text(encoding="utf-8").splitlines()), 3)

    def test_few_shot_prompt_uses_train_examples_and_changes_the_prompt_id(self):
        examples = select_examples(sample_items(), count=2)
        few_shot = ExtractionPrompt(examples)
        self.assertNotEqual(few_shot.prompt_id, ExtractionPrompt().prompt_id)
        self.assertEqual(len(few_shot.messages("pump noisy")), 2 + 2 * len(examples))


class CapabilityTests(unittest.TestCase):
    def test_probes_every_json_model_and_schema_only_where_supported(self):
        models = [{"id": "MiMo-V2.6-Flash", "json_output": True, "structured_outputs": True},
                  {"id": "GLM-5.3-Flash", "json_output": True, "structured_outputs": False},
                  {"id": "MinerU2.5-Pro", "json_output": False}]
        self.assertEqual(probe_plan(models), [("MiMo-V2.6-Flash", "json_object"), ("MiMo-V2.6-Flash", "json_schema"),
                                              ("GLM-5.3-Flash", "json_object")])
        script = [reply({"data": models}), reply(chat_reply('{"status": "ok", "component": "pump"}')),
                  reply({"error": {"message": "schema rejected"}}, 400), reply(chat_reply("", "length"))]
        with ScriptedServer(script) as server:
            matrix = capability_matrix(ChatClient(server.base_url, "rc-x"))
        statuses = [(row["model"], row["output_mode"], row["status"]) for row in matrix["probes"]]
        self.assertEqual(statuses, [("MiMo-V2.6-Flash", "json_object", "ok"), ("MiMo-V2.6-Flash", "json_schema", "bad_request"),
                                    ("GLM-5.3-Flash", "json_object", "truncated")])


if __name__ == "__main__":
    unittest.main()
