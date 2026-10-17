"""Paced benchmark runner: raw per-request rows plus a summary of quality, validity, latency and usage.

`latency_seconds` is the client-timed request-to-reply time of the successful attempt; `wall_seconds`
also includes pacing waits and retries. Rows that fail stay in every denominator. A small sample's p95
is preliminary.
"""

import json
import math
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ignis_wo.evaluation.scorer import entity_set, micro_scores, relation_set
from ignis_wo.extraction.adapters import gold_item_to_output
from ignis_wo.extraction.validate import validate_output
from ignis_wo.hosted.frozen import load_frozen_config
from ignis_wo.hosted.transport import RECORD_LEVEL_KINDS, STOP_KINDS, ProviderError

TEST_LEDGER = Path("outputs/eval_ledger.jsonl")
SCORED_OUTCOMES = RECORD_LEVEL_KINDS | {"valid", "invalid"}


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(percent / 100 * len(ordered)))
    return ordered[rank - 1]


def run_cases(cases: list[dict], call, concurrency: int = 1, max_duration_seconds: float = 600,
              clock=time.monotonic) -> tuple[list[dict], float]:
    """Calls `call(case)` for each case. Auth or credit failures stop every case not yet started."""
    stop = threading.Event()
    started = clock()

    def run_one(case: dict) -> dict:
        if stop.is_set() or clock() - started > max_duration_seconds:
            return {"case_id": case["case_id"], "status": "skipped"}
        began = clock()
        try:
            row = call(case)
        except ProviderError as error:
            row = {"status": error.kind, "error": str(error), "http_status": error.status}
            if error.kind in STOP_KINDS:
                stop.set()
        except Exception as error:  # noqa: BLE001 - one broken case must not lose rows already paid for
            row = {"status": "error", "error": f"{type(error).__name__}: {error}"}
        row["case_id"] = case["case_id"]
        row["wall_seconds"] = round(clock() - began, 3)
        row.setdefault("latency_seconds", None)
        return row

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        rows = list(pool.map(run_one, cases))
    return rows, clock() - started


def usage_total(rows: list[dict], key: str) -> int:
    return sum(row.get("usage", {}).get(key) or 0 for row in rows)


def reasoning_total(rows: list[dict]) -> int:
    details = [row.get("usage", {}).get("completion_tokens_details") or {} for row in rows]
    return sum(detail.get("reasoning_tokens") or 0 for detail in details)


def summarize(rows: list[dict], wall_seconds: float) -> dict:
    attempted = [row for row in rows if row["status"] != "skipped"]
    valid = [row for row in attempted if row["status"] == "valid"]
    latencies = [row["latency_seconds"] for row in attempted if row.get("latency_seconds") is not None]
    wall_times = [row["wall_seconds"] for row in attempted]
    minutes = wall_seconds / 60 if wall_seconds > 0 else None
    rate_rows = [row["rate_headers"] for row in attempted if row.get("rate_headers")]
    return {
        "cases": len(rows),
        "attempted": len(attempted),
        "skipped": len(rows) - len(attempted),
        "valid": len(valid),
        "outcomes": dict(sorted(Counter(row["status"] for row in attempted).items())),
        "retries": sum(max(row.get("attempts", 1) - 1, 0) for row in attempted),
        "spans_reanchored": sum(row.get("spans_reanchored", 0) for row in attempted),
        "latency_p50_seconds": percentile(latencies, 50),
        "latency_p95_seconds": percentile(latencies, 95),
        "wall_p50_seconds": percentile(wall_times, 50),
        "wall_p95_seconds": percentile(wall_times, 95),
        "wall_seconds": round(wall_seconds, 3),
        "attempted_per_minute": round(len(attempted) / minutes, 2) if minutes else None,
        "valid_per_minute": round(len(valid) / minutes, 2) if minutes else None,
        "prompt_tokens": usage_total(attempted, "prompt_tokens"),
        "completion_tokens": usage_total(attempted, "completion_tokens"),
        "reasoning_tokens": reasoning_total(attempted),
        "last_rate_headers": rate_rows[-1] if rate_rows else {},
    }


def extraction_cases(items: list[dict]) -> list[dict]:
    cases = []
    for index, item in enumerate(items):
        text_norm, gold = gold_item_to_output(item)
        cases.append({"case_id": f"item-{index}", "text_norm": text_norm, "gold": gold})
    return cases


def extraction_call(adapter):
    def call(case: dict) -> dict:
        response, result, reanchored = adapter.extract_with_result(case["text_norm"])
        output, errors = validate_output(response, case["text_norm"])
        return {"status": "valid" if output else "invalid", "errors": errors[:5], "attempts": result.attempts,
                "latency_seconds": result.latency_seconds, "spans_reanchored": reanchored,
                "finish_reason": result.finish_reason, "usage": result.usage, "rate_headers": result.rate_headers,
                "prediction": output.model_dump() if output else None}

    return call


def extraction_scores(cases: list[dict], rows: list[dict]) -> dict:
    """Skipped cases are excluded; failed or invalid ones count as empty predictions."""
    attempted = [(case, row) for case, row in zip(cases, rows) if row["status"] != "skipped"]
    gold_entities = [entity_set(case["gold"], None) for case, _ in attempted]
    predicted_entities = [entity_set(row.get("prediction"), None) for _, row in attempted]
    gold_relations = [relation_set(case["gold"]) for case, _ in attempted]
    predicted_relations = [relation_set(row.get("prediction")) for _, row in attempted]
    return {"entities": micro_scores(gold_entities, predicted_entities),
            "relations": micro_scores(gold_relations, predicted_relations)}


def write_results(directory: Path, rows: list[dict], summary: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "requests.jsonl").open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, sort_keys=True) + "\n")
    (directory / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_complete(summary: dict) -> bool:
    """Only a run where every case got a model answer may lock the test split for its configuration."""
    return summary["skipped"] == 0 and set(summary["outcomes"]) <= SCORED_OUTCOMES


def locking_entries(ledger: Path) -> list[dict]:
    """Entries marked incomplete are kept for audit but do not lock the configuration."""
    if not ledger.exists():
        return []
    entries = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [entry for entry in entries if entry.get("complete", True)]


def ledger_contains(ledger: Path, model_id: str, model_version: str) -> bool:
    return any(entry.get("model_id") == model_id and entry.get("model_version") == model_version
               for entry in locking_entries(ledger))


def ledger_contains_legacy(ledger: Path, adapter) -> bool:
    """A v1 entry (version without the budget label) locks the same model, prompt and explicit budget.
    v1 runs always sent an explicit max_tokens, 4096 unless recorded otherwise, and had no fallback."""
    legacy_model_version = getattr(adapter, "legacy_model_version", None)
    if legacy_model_version is None or adapter.budget_fallback:
        return False
    version = legacy_model_version()
    return any(entry.get("model_id") == adapter.model_id and entry.get("model_version") == version
               and entry.get("max_tokens", 4096) == adapter.max_tokens for entry in locking_entries(ledger))


def matches_scored_entry(adapter, scored: dict) -> bool:
    legacy_model_version = getattr(adapter, "legacy_model_version", None)
    if legacy_model_version is None:
        return False
    same_budget = adapter.max_tokens == scored["max_tokens"] and adapter.budget_fallback == scored["budget_fallback"]
    return adapter.model_id == scored["model_id"] and legacy_model_version() == scored["model_version"] and same_budget


def already_scored(ledger: Path, adapter, scored: dict | None = None) -> bool:
    """True when the local ledger or the committed frozen configuration says this setup was scored on test.
    The committed entry guards machines whose local ledger does not have the run."""
    if ledger_contains(ledger, adapter.model_id, adapter.model_version) or ledger_contains_legacy(ledger, adapter):
        return True
    return matches_scored_entry(adapter, scored or load_frozen_config()["scored_as"])
