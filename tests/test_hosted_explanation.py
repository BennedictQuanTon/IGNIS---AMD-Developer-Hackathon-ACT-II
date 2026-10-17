import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sample_data import frozen_config_for, sample_items

from ignis_wo.extraction.adapters import ReplayMiss
from ignis_wo.hosted.explanation import HostedExplanationProvider, assemble_draft
from ignis_wo.hosted.providers import providers_from_environment
from ignis_wo.hosted.transport import ChatResult, ProviderError
from ignis_wo.workflow.context import retrieve, validate_draft
from ignis_wo.workflow.service import Workflow


class ScriptedClient:
    """Returns scripted final answers in order, standing in for ChatClient.complete."""

    def __init__(self, *contents, error=None):
        self.contents = list(contents)
        self.error = error
        self.calls = []

    def complete(self, model, messages, output_mode, schema, reasoning_effort, max_tokens, budget_fallback=False):
        self.calls.append(messages)
        if self.error:
            raise self.error
        content = self.contents.pop(0)
        return ChatResult(json.dumps(content), None, "stop", {"prompt_tokens": 1}, {}, 0.1, 1, {"model": model})


def claim(text, citations, fact_ids=()):
    return {"text": text, "citations": list(citations), "fact_ids": list(fact_ids)}


def reduced(hypothesis_text="Seal leakage is described; its cause is unresolved.", citations=None, fact_ids=("F-a",)):
    return {"hypotheses": [claim(hypothesis_text, citations or ["MAN-PUMP-A-v1"], fact_ids)], "alternatives": [],
            "uncertainty": "Causation is unresolved.",
            "inspection": claim("Check whether the flush line is obstructed.", ["MAN-PUMP-A-v1"]), "abstain": False}


class ExplanationProviderTests(unittest.TestCase):
    def setUp(self):
        fact = {"fact_id": "F-a", "snapshot_id": "S-1", "kind": "severity", "scope": {"component": "seal"}, "value": 2,
                "unit": "severity_points", "status": "computed", "record_ids": ["WO-1"]}
        self.pack = retrieve("PUMP-SYN-01", "seal", "seal leakage flush", [fact], "S-1")["pack"]

    def test_bindings_are_copied_from_the_pack_not_the_model(self):
        draft = assemble_draft(self.pack, reduced())
        binding = draft["hypotheses"][0]["fact_bindings"][0]
        self.assertEqual(binding, {"fact_id": "F-a", "value": 2.0, "unit": "severity_points", "scope": {"component": "seal"},
                                   "snapshot_id": "S-1"})
        self.assertIn("F-a", draft["hypotheses"][0]["citations"])
        self.assertEqual(draft["pack_id"], self.pack["pack_id"])
        self.assertEqual(validate_draft(self.pack, draft), [])

    def test_valid_first_answer_needs_one_call(self):
        client = ScriptedClient(reduced())
        provider = HostedExplanationProvider(client, "GLM-5.3-Flash")
        self.assertEqual(validate_draft(self.pack, provider(self.pack)), [])
        self.assertEqual(len(client.calls), 1)
        self.assertIn("MAN-PUMP-A-v1", client.calls[0][1]["content"])

    def test_number_words_get_one_repair_round_with_the_errors(self):
        client = ScriptedClient(reduced("The first likely issue is the seal."), reduced())
        draft = HostedExplanationProvider(client, "GLM-5.3-Flash")(self.pack)
        self.assertEqual(validate_draft(self.pack, draft), [])
        self.assertEqual(len(client.calls), 2)
        self.assertIn("numbers in prose", client.calls[1][-1]["content"])

    def test_unknown_citation_stays_visible_to_the_validator(self):
        invented = reduced(citations=["MAN-PUMP-B-v1"])
        draft = HostedExplanationProvider(ScriptedClient(invented, invented), "m")(self.pack)
        self.assertIn("citation 'MAN-PUMP-B-v1' is not in the pack", validate_draft(self.pack, draft))

    def test_no_facts_and_no_passages_abstains_without_a_call(self):
        empty_pack = {**self.pack, "facts": [], "passages": []}
        client = ScriptedClient()
        draft = HostedExplanationProvider(client, "m")(empty_pack)
        self.assertTrue(draft["abstain"])
        self.assertEqual(client.calls, [])
        self.assertEqual(validate_draft(empty_pack, draft), [])

    def test_v3_computed_facts_without_passages_abstain_without_inference(self):
        pack = {**self.pack, "passages": []}
        client = ScriptedClient(reduced())
        draft, attempts = HostedExplanationProvider(client, "m", prompt_version="v3").draft_with_attempts(pack)
        self.assertTrue(draft["abstain"])
        self.assertEqual(draft["hypotheses"], [])
        self.assertEqual(draft["alternatives"], [])
        self.assertIsNone(draft["inspection"])
        self.assertEqual(client.calls, [])
        self.assertEqual(attempts, [])
        self.assertEqual(validate_draft(pack, draft), [])

    def test_v3_repairs_the_observed_number_word_failure_without_weakening_validation(self):
        client = ScriptedClient(reduced("There is at least one failed-state record."), reduced())
        provider = HostedExplanationProvider(client, "m", prompt_version="v3")
        draft = provider(self.pack)
        self.assertEqual(validate_draft(self.pack, draft), [])
        self.assertEqual(len(client.calls), 2)
        self.assertIn("at least one", client.calls[1][-1]["content"])
        self.assertIn("fact_ids", client.calls[1][-1]["content"])
        invalid = assemble_draft(self.pack, reduced("There is at least one failed-state record."))
        self.assertIn("numbers in prose must be rendered from typed fact slots", validate_draft(self.pack, invalid))

    def test_all_prompt_versions_replay_under_their_original_identity(self):
        from ignis_wo.hosted.prompts import ExplanationPrompt
        self.assertEqual(ExplanationPrompt("v1").prompt_id, "explanation-draft-v1-555c9aee")
        self.assertEqual(ExplanationPrompt("v2").prompt_id, "explanation-draft-v2-f80d1254")
        for version in ("v1", "v2", "v3"):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "reply.jsonl"
                provider = HostedExplanationProvider(ScriptedClient(reduced()), "m", prompt_version=version, record_path=path)
                expected = provider(self.pack)
                replay = HostedExplanationProvider(None, "m", replay_path=path)
                self.assertEqual(replay(self.pack), expected)
                self.assertEqual(replay.prompt_id, provider.prompt_id)

    def test_the_replay_key_changes_with_the_budget_and_reasoning(self):
        key = HostedExplanationProvider(None, "m").replay_key(self.pack, 0)
        variants = [HostedExplanationProvider(None, "m", max_tokens=None),
                    HostedExplanationProvider(None, "m", budget_fallback=True),
                    HostedExplanationProvider(None, "m", reasoning_effort=None)]
        for provider in variants:
            self.assertNotEqual(provider.replay_key(self.pack, 0), key)

    def test_recorded_answers_replay_and_a_changed_pack_misses(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "explanation.jsonl"
            live = HostedExplanationProvider(ScriptedClient(reduced()), "m", record_path=path)
            first = live(self.pack)
            replay = HostedExplanationProvider(None, "m", replay_path=path)
            self.assertEqual(replay(self.pack), first)
            self.assertEqual(replay.explanation_mode, "hosted_replay")
            with self.assertRaises(ReplayMiss):
                replay({**self.pack, "pack_id": "EP-changed"})

    def test_new_prompt_avoids_identifiers_and_legacy_recordings_keep_their_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.jsonl"
            client = ScriptedClient(reduced())
            legacy = HostedExplanationProvider(client, "m", prompt_version="v1", record_path=path)
            original = legacy(self.pack)
            replay = HostedExplanationProvider(None, "m", replay_path=path)
            current = HostedExplanationProvider(ScriptedClient(reduced()), "m")
            self.assertEqual(replay(self.pack), original)
            self.assertEqual(replay.prompt_id, legacy.prompt_id)
            self.assertNotEqual(current.replay_key(self.pack, 0), legacy.replay_key(self.pack, 0))
            self.assertIn("never 'PX-100'", current.prompt.system)
            invalid = assemble_draft(self.pack, reduced("The PX-100 pump has seal leakage."))
            self.assertIn("numbers in prose must be rendered from typed fact slots", validate_draft(self.pack, invalid))
            with self.assertRaisesRegex(ValueError, "cannot be relabelled"):
                HostedExplanationProvider(None, "m", replay_path=path, prompt_version="v2")


class WorkflowIntegrationTests(unittest.TestCase):
    def run_to_context(self, provider):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        workflow = Workflow(root / "state.sqlite3", root, sample_items(), explanation_provider=provider)
        run = workflow.create_run("hosted explanation", "tester", True, "fixture")
        run_id = run["run_id"]
        rows = [f"WO-{index},PUMP-SYN-01,2025-01-{index:02d},pump seal leaking,1.0" for index in range(1, 5)]
        csv_text = "WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h)\n" + "\n".join(rows) + "\n"
        state = workflow.upload(run_id, run["revision"], "synthetic.csv", csv_text)
        state = workflow.confirm_mapping(run_id, state["revision"], state["proposal"]["mapping"], "test headers")
        state = workflow.extract(run_id, state["revision"])
        for record in state["records"]:
            state = workflow.review(run_id, state["revision"], record["record_id"], "accepted", "test", reviewer="tester")
        state = workflow.analyze(run_id, state["revision"], [])
        state = workflow.build_context(run_id, state["revision"], "PUMP-SYN-01", "seal", "seal leakage flush")
        return workflow.generate_context_draft(run_id, state["revision"])["draft_result"]

    def test_hosted_provider_reaches_expert_review_with_its_provenance(self):
        provider = HostedExplanationProvider(ScriptedClient(reduced(fact_ids=())), "GLM-5.3-Flash")
        result = self.run_to_context(provider)
        self.assertEqual(result["status"], "pending_expert_review", result["errors"])
        self.assertEqual(result["model_id"], "GLM-5.3-Flash")
        self.assertEqual(result["explanation_mode"], "hosted_live")
        self.assertTrue(result["prompt_id"].startswith("explanation-draft-v3-"))

    def test_provider_outage_is_recorded_as_an_invalid_draft(self):
        provider = HostedExplanationProvider(ScriptedClient(error=ProviderError("unavailable", "down")), "m")
        result = self.run_to_context(provider)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("unavailable", result["errors"][0])


class EnvironmentTests(unittest.TestCase):
    def test_v3_is_the_live_default_and_v2_stays_selectable(self):
        environment = {"MODEL_API_KEY": "test-key", "EXPLANATION_MODEL_NAME": "m"}
        _, default = providers_from_environment(environment)
        self.assertEqual(default.prompt.version, "v3")
        _, previous = providers_from_environment({**environment, "EXPLANATION_PROMPT_VERSION": "v2"})
        self.assertEqual(previous.prompt.version, "v2")

    def test_no_model_names_means_no_providers(self):
        self.assertEqual(providers_from_environment({}), (None, None))

    def test_explanation_alone_needs_no_maintie_data(self):
        environment = {"MODEL_API_KEY": "rc-x", "EXPLANATION_MODEL_NAME": "GLM-5.3-Flash"}
        with mock.patch("ignis_wo.hosted.providers.load_train_items", side_effect=AssertionError("data was read")):
            extraction, explanation = providers_from_environment(environment)
        self.assertIsNone(extraction)
        self.assertEqual(explanation.model_id, "GLM-5.3-Flash")

    def test_a_model_without_a_key_is_refused(self):
        with self.assertRaises(ValueError):
            providers_from_environment({"MODEL_NAME": "DeepSeek-V4-Flash"})

    def test_configured_providers_carry_model_identity(self):
        environment = {"MODEL_API_KEY": "rc-x", "MODEL_NAME": "DeepSeek-V4-Flash", "EXPLANATION_MODEL_NAME": "GLM-5.3-Flash"}
        config = frozen_config_for(sample_items(), "DeepSeek-V4-Flash")
        extraction, explanation = providers_from_environment(environment, max_records=1, train_items=sample_items(),
                                                             frozen_config=config)
        self.assertEqual(extraction.model_id, "DeepSeek-V4-Flash")
        self.assertTrue(extraction.scored_configuration)
        self.assertEqual(explanation.model_id, "GLM-5.3-Flash")
        self.assertTrue(explanation.budget_fallback)
        with self.assertRaises(ValueError):
            extraction([object(), object()])


if __name__ == "__main__":
    unittest.main()
