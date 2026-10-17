import json
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree
from pathlib import Path

from mock_chat_server import ScriptedServer, chat_reply, reply

from ignis_wo.evaluation.charts import grouped_bars
from ignis_wo.evaluation.explanation_benchmark import (
    load_scenarios,
    run_family,
    scenario_lock,
    scenario_pack,
    summarize_model,
    write_blind_sheet,
)
from ignis_wo.evaluation.jobs import JobBudget
from ignis_wo.evaluation.reader_benchmark import FAMILIES, family_files, normalized, score_page
from ignis_wo.hosted.explanation import HostedExplanationProvider
from ignis_wo.hosted.providers import replay_providers
from ignis_wo.hosted.transport import ChatClient, ChatResult, Gateway, ProviderError


ROOT = Path(__file__).resolve().parents[1]


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class ScriptedClient:
    def __init__(self, *answers):
        self.answers = list(answers)

    def complete(self, model, messages, output_mode, schema, reasoning_effort, max_tokens, budget_fallback=False):
        answer = self.answers.pop(0)
        return ChatResult(json.dumps(answer), None, "stop", {"prompt_tokens": 10, "completion_tokens": 5}, {}, 0.5, 1,
                          {"model": model})


def claim(text, citations):
    return {"text": text, "citations": citations, "fact_ids": []}


def answer(citations, abstain=False, text="Seal leakage is described; its cause is unresolved."):
    hypotheses = [] if abstain else [claim(text, citations)]
    return {"hypotheses": hypotheses, "alternatives": [], "uncertainty": "Causation is unresolved.",
            "inspection": None, "abstain": abstain}


class ReaderMetricTests(unittest.TestCase):
    def test_perfect_and_degraded_reads_are_scored_per_page(self):
        gold = FAMILIES["F2-table-pdf"]["pages"][1]
        perfect = score_page(gold, "\n".join(gold["lines"]))
        self.assertEqual((perfect["cer"], perfect["wer"], perfect["critical_missing"]), (0.0, 0.0, []))
        self.assertEqual(perfect["table_rows_correct"], 2)
        damaged = score_page(gold, "\n".join(gold["lines"]).replace("4.25", "425").replace("not confirmed", "confirmed"))
        self.assertIn("4.25", damaged["numbers_missing"])
        self.assertIn("not confirmed", damaged["critical_missing"])
        self.assertGreater(damaged["cer"], 0)

    def test_html_tables_are_matched_by_row(self):
        gold = FAMILIES["F5-table-image"]["pages"][0]
        rows = "".join(f"<tr>{''.join(f'<td>{cell}</td>' for cell in row)}</tr>" for row in gold["rows"])
        self.assertEqual(score_page(gold, f"<table>{rows}</table>")["table_rows_correct"], 2)
        self.assertEqual(normalized("<td>| **P-7741** |</td>"), "P-7741")

    def test_every_family_generates_two_gold_pages(self):
        for name, family in FAMILIES.items():
            pages = [page for _, _, numbers in family_files(name, family) for page in numbers]
            self.assertEqual(pages, [0, 1], name)


class ScenarioTests(unittest.TestCase):
    def test_the_locked_file_splits_twelve_dev_and_eight_held_out(self):
        self.assertEqual((len(load_scenarios("dev")), len(load_scenarios("heldout"))), (12, 8))

    def test_a_changed_scenario_file_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "pump_scenarios.json"
            text = load_scenarios.__defaults__[1].read_text(encoding="utf-8")
            changed.write_text(text.replace("S01-MAN", "S01-MAN-X"), encoding="utf-8")
            lock = Path(directory) / "lock.json"
            lock.write_text(json.dumps(scenario_lock()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                load_scenarios(None, changed, lock)

    def test_packs_never_hold_expected_answers_or_wrong_model_passages(self):
        for family in load_scenarios():
            pack = scenario_pack(family)["pack"]
            self.assertNotIn("expected", json.dumps(pack))
            model = family["graph"]["assets"][family["asset_id"]]["model"]
            wrong = {item["passage_id"] for item in family["corpus"]["documents"] if item["asset_model"] != model}
            self.assertFalse(wrong & {passage["passage_id"] for passage in pack["passages"]}, family["family_id"])


class ExplanationScoringTests(unittest.TestCase):
    def setUp(self):
        self.families = {family["family_id"]: family for family in load_scenarios()}

    def test_first_pass_and_repaired_validity_are_separate(self):
        first = answer(["S01-MAN"], text="Seal leakage is the first issue.")
        provider = HostedExplanationProvider(ScriptedClient(first, answer(["S01-MAN"])), "m")
        row = run_family(self.families["S01"], provider, clock=FakeClock())
        self.assertEqual((row["first_pass_valid"], row["valid"], row["calls"]), (False, True, 2))
        self.assertTrue(row["support_hit"])
        self.assertTrue(row["outcome_correct"])

    def test_abstention_and_distractor_citations_are_scored(self):
        abstained = run_family(self.families["S05"], HostedExplanationProvider(ScriptedClient(answer([], True)), "m"))
        self.assertTrue(abstained["outcome_correct"])
        distracted = run_family(self.families["S10"], HostedExplanationProvider(ScriptedClient(answer(["S10-LABEL"])), "m"))
        self.assertEqual((distracted["support_hit"], distracted["distractor_cited"]), (False, True))
        summary = summarize_model([abstained, distracted])
        self.assertEqual(summary["outcome_correct"], {"true": 2, "n": 2})
        self.assertEqual(summary["support_hit"], {"true": 0, "n": 1})

    def test_stop_errors_end_the_job_and_others_fail_one_family(self):
        class Failing:
            model_id = "m"

            def __init__(self, kind):
                self.kind = kind

            def draft_with_attempts(self, pack):
                raise ProviderError(self.kind, "failed")

        with self.assertRaises(ProviderError):
            run_family(self.families["S01"], Failing("job_budget"))
        self.assertEqual(run_family(self.families["S01"], Failing("timeout"))["error"], "timeout")

    def test_a_failed_repair_keeps_the_earlier_attempt(self):
        class RepairTimesOut(ScriptedClient):
            def complete(self, *arguments, **options):
                if not self.answers:
                    raise ProviderError("timeout", "no reply")
                return super().complete(*arguments, **options)

        first = answer(["S01-MAN"], text="Seal leakage is the first issue.")
        row = run_family(self.families["S01"], HostedExplanationProvider(RepairTimesOut(first), "m"))
        self.assertEqual((row["error"], row["calls"], row["model_seconds"], row["prompt_tokens"]), ("timeout", 1, 0.5, 10))

    def test_the_blind_sheet_hides_model_names(self):
        rows = [run_family(self.families["S01"], HostedExplanationProvider(ScriptedClient(answer(["S01-MAN"])), name))
                for name in ("Model-A", "Model-B")]
        with tempfile.TemporaryDirectory() as directory:
            sheet, key = Path(directory) / "sheet.csv", Path(directory) / "key.json"
            self.assertEqual(write_blind_sheet(rows, self.families, sheet, key, seed=1), 2)
            self.assertNotIn("Model-", sheet.read_text(encoding="utf-8"))
            self.assertEqual({entry["model_id"] for entry in json.loads(key.read_text()).values()}, {"Model-A", "Model-B"})


class JobBudgetTests(unittest.TestCase):
    def test_attempt_and_time_caps_stop_before_sending(self):
        clock = FakeClock()
        budget = JobBudget("test", max_attempts=2, max_seconds=60, clock=clock)
        with ScriptedServer([reply(chat_reply("{}"))]) as server:
            gateway = Gateway(server.base_url, "rc-test")
            gateway.budget = budget
            client = ChatClient(gateway=gateway)
            client.complete("m", [{"role": "user", "content": "hi"}])
            client.complete("m", [{"role": "user", "content": "hi"}])
            with self.assertRaises(ProviderError) as caught:
                client.complete("m", [{"role": "user", "content": "hi"}])
        self.assertEqual((caught.exception.kind, len(server.requests)), ("job_budget", 2))
        later = JobBudget("test", max_attempts=5, max_seconds=60, clock=clock)
        clock.now = 61
        with self.assertRaises(ProviderError):
            later.spend("POST", "/x")

    def test_quota_snapshots_come_only_from_successful_replies(self):
        budget = JobBudget("test")
        ok = budget.spend("POST", "/chat/completions")
        budget.settle(ok, "ok", {"x-ratelimit-remaining-user-daily-usd": "0.8"})
        failed = budget.spend("POST", "/chat/completions")
        budget.settle(failed, "unavailable")
        summary = budget.summary()
        self.assertEqual(summary["outcomes"], {"ok": 1, "unavailable": 1})
        self.assertEqual(summary["quota_last"], {"x-ratelimit-remaining-user-daily-usd": "0.8"})


class CommandGuardTests(unittest.TestCase):
    def run_script(self, *arguments):
        command = [sys.executable, str(ROOT / "scripts" / arguments[0]), *arguments[1:]]
        return subprocess.run(command, capture_output=True, text=True, cwd=ROOT, check=False)

    def test_a_final_run_with_too_few_attempts_is_refused_before_any_call(self):
        result = self.run_script("run_benchmark.py", "--split", "test", "--final", "--model", "m", "--limit", "108")
        self.assertIn("--max-attempts 118", result.stderr)

    def test_rescoring_repeated_runs_is_refused(self):
        self.assertIn("cannot separate repeated runs", self.run_script("benchmark_explanations.py", "repeat", "--rescore").stderr)


class ChartTests(unittest.TestCase):
    def test_grouped_bars_parse_and_mark_missing_values(self):
        svg = grouped_bars("Quality & speed", ["a", "b"], {"Model <1>": [50.0, None], "Model 2": [10.0, 20.0]}, "%", 100)
        root = ElementTree.fromstring(svg)
        titles = [element.text for element in root.iter("{http://www.w3.org/2000/svg}title")]
        self.assertEqual(len(titles), 3)
        self.assertIn("n/a", svg)
        self.assertIn("prefers-color-scheme: dark", svg)


class ReplayServingTests(unittest.TestCase):
    def test_replay_providers_need_no_key_and_fail_on_a_missing_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaisesRegex(ValueError, "no extraction-replay"):
                replay_providers(folder)
            family = load_scenarios("dev")[0]
            pack = scenario_pack(family)["pack"]
            recorder = HostedExplanationProvider(ScriptedClient(answer(["S01-MAN"])), "m", budget_fallback=True,
                                                 record_path=folder / "explanation-replay.jsonl")
            recorded = recorder(pack)
            extraction, explanation = replay_providers(folder)
            self.assertIsNone(extraction)
            self.assertEqual((explanation(pack), explanation.explanation_mode), (recorded, "hosted_replay"))


if __name__ == "__main__":
    unittest.main()
