"""#23 Stage 2: compare explanation models on identical frozen evidence packs.

Packs are built by code (`context.retrieve` over each scenario's reviewed mini corpus); the expected
outcome never enters a pack or prompt. Automatic metrics cover structure, references, abstention and
which passages were cited. Whether a claim is semantically supported by its passage is not scored
automatically: it goes to a blind human rating sheet.
"""

import csv
import json
import random
import re
import time
from pathlib import Path

from ignis_wo.evaluation.benchmark import percentile
from ignis_wo.hashing import sha256_text
from ignis_wo.hosted.transport import STOP_KINDS, ProviderError
from ignis_wo.workflow.context import retrieve

IDENTIFIER = re.compile(r"\b[A-Z]+-\d+\b")
DIGIT_TOKEN = re.compile(r"\S*\d\S*")
SCENARIOS = Path(__file__).resolve().parents[2] / "docs" / "benchmarks" / "scenarios" / "pump_scenarios.json"
LOCK = SCENARIOS.with_name("scenario_lock.json")


def scenario_lock(path: Path = SCENARIOS) -> dict:
    families = json.loads(path.read_text(encoding="utf-8"))["families"]
    splits = {split: [item["family_id"] for item in families if item["split"] == split] for split in ("dev", "heldout")}
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return {"sha256": sha256_text(text), **splits}


def load_scenarios(split: str | None = None, path: Path = SCENARIOS, lock_path: Path = LOCK) -> list[dict]:
    """Refuses to run when the scenario file differs from its committed lock."""
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if scenario_lock(path) != lock:
        raise ValueError("scenario file does not match scenario_lock.json; held-out cases may have changed")
    families = json.loads(path.read_text(encoding="utf-8"))["families"]
    return [item for item in families if split is None or item["split"] == split]


def scenario_pack(family: dict) -> dict:
    sources = (family["corpus"], family["graph"])
    return retrieve(family["asset_id"], family["component"], family["query"], family["facts"], family["snapshot_id"],
                    sources)


def claim_citations(draft: dict, labels: tuple[str, ...]) -> set[str]:
    """Malformed claims (e.g. bare strings) cite nothing; the validator already rejects them."""
    claims = [claim for label in labels for claim in draft.get(label) or []]
    if "inspection" in labels and draft.get("inspection"):
        claims.append(draft["inspection"])
    return {citation for claim in claims if isinstance(claim, dict) for citation in claim.get("citations") or []}


def prose_texts(draft: dict) -> list[str]:
    claims = [*(draft.get("hypotheses") or []), *(draft.get("alternatives") or []), draft.get("inspection")]
    texts = [claim.get("text", "") if isinstance(claim, dict) else str(claim or "") for claim in claims]
    return [*texts, draft.get("uncertainty") or ""]


def only_identifier_digits(draft: dict, errors: list[str]) -> bool:
    """Diagnostic: the sole error is the number rule, and every digit sits in an identifier such as PX-100."""
    if errors != ["numbers in prose must be rendered from typed fact slots"]:
        return False
    stripped = [IDENTIFIER.sub("", text) for text in prose_texts(draft)]
    return not any(DIGIT_TOKEN.search(text) for text in stripped)


def scored_row(family: dict, model_id: str, retrieved: dict, draft: dict | None, attempts: list[dict]) -> dict:
    expected = family["expected"]
    wrong_model = {item["passage_id"] for item in family["corpus"]["documents"]
                   if item["asset_model"] != family["graph"]["assets"][family["asset_id"]]["model"]}
    passages = [passage["passage_id"] for passage in (retrieved["pack"] or {}).get("passages", [])]
    row = {"family_id": family["family_id"], "split": family["split"], "trap": family["trap"], "model_id": model_id,
           "context_status": retrieved["status"], "pack_passages": passages,
           "wrong_model_in_pack": sorted(set(passages) & wrong_model), "calls": len(attempts),
           "first_pass_valid": bool(attempts) and not attempts[0]["errors"],
           "final_errors": attempts[-1]["errors"] if attempts else [],
           "model_seconds": round(sum(attempt["latency_seconds"] or 0 for attempt in attempts), 3),
           "completion_tokens": sum(attempt["usage"].get("completion_tokens", 0) for attempt in attempts),
           "prompt_tokens": sum(attempt["usage"].get("prompt_tokens", 0) for attempt in attempts),
           "budget_fallback": any("budget_fallback" in attempt["request_parameters"] for attempt in attempts)}
    if draft is None:
        return {**row, "valid": False}
    hypotheses = claim_citations(draft, ("hypotheses",))
    cited = claim_citations(draft, ("hypotheses", "alternatives", "inspection"))
    abstain_expected = expected["outcome"] == "abstain"
    return {**row, "valid": not row["final_errors"], "abstained": draft["abstain"],
            "outcome_correct": draft["abstain"] == abstain_expected,
            "support_hit": None if abstain_expected else bool(hypotheses & set(expected["supporting_passages"])),
            "distractor_cited": bool(cited & set(expected["distractor_passages"])) if expected["distractor_passages"] else None,
            "number_violation": any("numbers in prose" in error for error in row["final_errors"]),
            "only_identifier_digits": only_identifier_digits(draft, row["final_errors"]),
            "draft": draft}


def run_family(family: dict, provider, clock=time.monotonic) -> dict:
    retrieved = scenario_pack(family)
    began = clock()
    draft, attempts = None, []
    if retrieved["pack"] is not None:
        try:
            draft, attempts = provider.draft_with_attempts(retrieved["pack"])
        except ProviderError as error:
            if error.kind in STOP_KINDS:
                raise
            row = scored_row(family, provider.model_id, retrieved, None, getattr(error, "attempts", []))
            return {**row, "error": error.kind, "message": str(error), "full_path_seconds": round(clock() - began, 3)}
    row = scored_row(family, provider.model_id, retrieved, draft, attempts)
    return {**row, "full_path_seconds": round(clock() - began, 3)}


def rate(rows: list[dict], key: str) -> dict:
    values = [row[key] for row in rows if row.get(key) is not None]
    return {"true": sum(bool(value) for value in values), "n": len(values)}


def summarize_model(rows: list[dict]) -> dict:
    latencies = [row["model_seconds"] for row in rows if row["calls"]]
    valid = [row for row in rows if row["valid"]]
    tokens = sum(row["completion_tokens"] + row["prompt_tokens"] for row in rows)
    return {"families": len(rows), "errors": sum("error" in row for row in rows),
            "first_pass_valid": rate(rows, "first_pass_valid"), "valid_after_repair": rate(rows, "valid"),
            "outcome_correct": rate(rows, "outcome_correct"), "support_hit": rate(rows, "support_hit"),
            "distractor_cited": rate(rows, "distractor_cited"),
            "invalid_only_for_identifier_digits": sum(bool(row.get("only_identifier_digits")) for row in rows),
            "wrong_model_in_pack": sum(bool(row["wrong_model_in_pack"]) for row in rows),
            "budget_fallback_used": sum(row["budget_fallback"] for row in rows),
            "model_seconds_p50": percentile(latencies, 50), "model_seconds_p95": percentile(latencies, 95),
            "latency_n": len(latencies), "calls": sum(row["calls"] for row in rows),
            "tokens_per_valid_output": round(tokens / len(valid), 1) if valid else None}


def described(label: str, claim) -> str:
    if not isinstance(claim, dict):
        return f"{label} (malformed): {claim}"
    return f"{label}: {claim.get('text', '')} [{', '.join(claim.get('citations') or [])}]"


def claim_text(draft: dict) -> str:
    parts = [described("Hypothesis", claim) for claim in draft.get("hypotheses") or []]
    parts += [described("Alternative", claim) for claim in draft.get("alternatives") or []]
    if draft.get("inspection"):
        parts.append(described("Inspection", draft["inspection"]))
    parts.append(f"Uncertainty: {draft['uncertainty']}; abstain: {draft['abstain']}")
    return "\n".join(parts)


def write_blind_sheet(rows: list[dict], families: dict, sheet_path: Path, key_path: Path, seed: int) -> int:
    """Model names are replaced by random rating ids; the key goes to a separate file for unblinding."""
    rated = [row for row in rows if row.get("draft")]
    random.Random(seed).shuffle(rated)
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["rating_id", "family_id", "query", "evidence", "draft", "semantic_support_0_2", "unsupported_claims",
               "useful_0_2", "rater", "notes"]
    key = {}
    with sheet_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, columns)
        writer.writeheader()
        for number, row in enumerate(rated, 1):
            rating_id = f"R{number:03d}"
            key[rating_id] = {"model_id": row["model_id"], "family_id": row["family_id"]}
            family = families[row["family_id"]]
            texts = {item["passage_id"]: item["text"] for item in family["corpus"]["documents"]}
            evidence = "\n".join(f"{passage}: {texts[passage]}" for passage in row["pack_passages"])
            writer.writerow({"rating_id": rating_id, "family_id": row["family_id"], "query": family["query"],
                             "evidence": evidence, "draft": claim_text(row["draft"])})
    key_path.write_text(json.dumps(key, indent=2), encoding="utf-8")
    return len(rated)
