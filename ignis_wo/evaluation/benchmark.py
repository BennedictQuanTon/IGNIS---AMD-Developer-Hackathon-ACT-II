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


def ledger_contains(ledger: Path, model_id: str, model_version: str) -> bool:
    """Entries marked incomplete are kept for audit but do not lock the configuration."""
    if not ledger.exists():
        return False
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        same_configuration = entry.get("model_id") == model_id and entry.get("model_version") == model_version
        if same_configuration and entry.get("complete", True):
            return True
    return False
