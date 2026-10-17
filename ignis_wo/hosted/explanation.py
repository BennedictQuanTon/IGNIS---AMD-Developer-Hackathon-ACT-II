"""Hosted explanation provider for the workflow's `explanation_provider(pack) -> dict` slot.

The model chooses claims, citations and which facts it relies on. Code fills `pack_id` and copies
each fact binding from the pack, so numbers, units, scopes and snapshot IDs never come from the model.
"""

import json
import threading
from pathlib import Path

from ignis_wo.extraction.adapters import ReplayMiss
from ignis_wo.hashing import sha256_text
from ignis_wo.hosted.prompts import EXPLANATION_SCHEMA, ExplanationPrompt
from ignis_wo.hosted.transport import budget_label, parse_json_content
from ignis_wo.workflow.context import validate_draft

TASK = "ignis-explanation-v1"
NO_EVIDENCE = "The evidence pack has no computed facts or applicable passages, so no explanation is drafted."


def bindable_facts(pack: dict) -> dict[str, dict]:
    return {fact["fact_id"]: fact for fact in pack["facts"]
            if fact.get("status") == "computed" and fact.get("value") is not None}


def binding_for(fact: dict) -> dict:
    return {"fact_id": fact["fact_id"], "value": float(fact["value"]), "unit": fact["unit"],
            "scope": fact["scope"], "snapshot_id": fact["snapshot_id"]}


def assemble_claim(raw_claim, facts: dict[str, dict]):
    if not isinstance(raw_claim, dict):
        return raw_claim
    citations = list(raw_claim.get("citations") or [])
    bindings = []
    for fact_id in raw_claim.get("fact_ids") or []:
        if fact_id in facts:
            bindings.append(binding_for(facts[fact_id]))
        if fact_id not in citations:
            citations.append(fact_id)
    return {"text": raw_claim.get("text", ""), "citations": citations, "fact_bindings": bindings}


def assemble_draft(pack: dict, reduced: dict) -> dict:
    """Unknown citations are kept so the validator rejects them instead of hiding the error."""
    facts = bindable_facts(pack)
    inspection = reduced.get("inspection")
    return {
        "pack_id": pack["pack_id"],
        "hypotheses": [assemble_claim(claim, facts) for claim in reduced.get("hypotheses") or []],
        "alternatives": [assemble_claim(claim, facts) for claim in reduced.get("alternatives") or []],
        "uncertainty": reduced.get("uncertainty") or "",
        "inspection": assemble_claim(inspection, facts) if inspection else None,
        "abstain": bool(reduced.get("abstain", False)),
    }


def abstain_draft(pack: dict) -> dict:
    return {"pack_id": pack["pack_id"], "hypotheses": [], "alternatives": [], "uncertainty": NO_EVIDENCE,
            "inspection": None, "abstain": True}


def load_responses(replay_path: Path) -> dict[str, dict]:
    responses = {}
    for line in replay_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            responses[row["key"]] = row["response"]
    return responses


class HostedExplanationProvider:
    def __init__(self, client, model_id: str, output_mode: str = "json_object", reasoning_effort: str | None = "low",
                 max_tokens: int | None = 4096, repair_attempts: int = 1, record_path: Path | None = None,
                 replay_path: Path | None = None, budget_fallback: bool = False):
        self.client = client
        self.model_id = model_id
        self.output_mode = output_mode
        self.reasoning_effort = reasoning_effort
        self.max_tokens = max_tokens
        self.budget_fallback = budget_fallback
        self.repair_attempts = repair_attempts
        self.record_path = record_path
        self.prompt = ExplanationPrompt()
        self.prompt_id = self.prompt.prompt_id
        self.responses = load_responses(replay_path) if replay_path else None
        self.explanation_mode = "hosted_replay" if replay_path else "hosted_live"
        self.lock = threading.Lock()

    def __call__(self, pack: dict) -> dict:
        if not bindable_facts(pack) and not pack["passages"]:
            return abstain_draft(pack)
        messages = self.prompt.messages(pack)
        for attempt in range(self.repair_attempts + 1):
            reduced = self.reduced_draft(pack, messages, attempt)
            draft = assemble_draft(pack, reduced)
            errors = validate_draft(pack, draft)
            if not errors:
                return draft
            messages = messages + self.prompt.repair_messages(reduced, errors)
        return draft

    def replay_key(self, pack: dict, attempt: int) -> str:
        budget = budget_label(self.max_tokens, self.budget_fallback)
        parts = [TASK, self.model_id, self.prompt_id, self.output_mode, self.reasoning_effort or "default", budget,
                 pack["pack_id"], str(attempt)]
        return sha256_text("|".join(parts))

    def reduced_draft(self, pack: dict, messages: list[dict], attempt: int) -> dict:
        key = self.replay_key(pack, attempt)
        if self.responses is not None:
            if key not in self.responses:
                raise ReplayMiss(f"no recorded explanation for pack {pack['pack_id']} attempt {attempt}")
            return self.responses[key]
        schema = EXPLANATION_SCHEMA if self.output_mode == "json_schema" else None
        result = self.client.complete(self.model_id, messages, self.output_mode, schema, self.reasoning_effort,
                                      self.max_tokens, budget_fallback=self.budget_fallback)
        reduced = parse_json_content(result.content)
        self.record(key, pack, attempt, reduced, result)
        return reduced

    def record(self, key: str, pack: dict, attempt: int, reduced: dict, result) -> None:
        if self.record_path is None:
            return
        row = {"key": key, "task": TASK, "model_id": self.model_id, "prompt_id": self.prompt_id,
               "output_mode": self.output_mode, "pack_id": pack["pack_id"], "attempt": attempt, "response": reduced,
               "finish_reason": result.finish_reason, "usage": result.usage, "latency_seconds": result.latency_seconds,
               "request_parameters": result.request_parameters}
        with self.lock, self.record_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(row, sort_keys=True) + "\n")
