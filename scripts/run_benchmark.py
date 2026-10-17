"""Benchmark hosted extraction on a verified MaintIE split through the AMD API.

Run with: uv run --env-file .env --no-project --with-requirements requirements-dev.txt python scripts/run_benchmark.py
The dev split is the default. The test split needs --final and runs once per model configuration.
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.evaluation.benchmark import (  # noqa: E402
    TEST_LEDGER,
    already_scored,
    extraction_call,
    extraction_cases,
    extraction_scores,
    run_cases,
    run_complete,
    summarize,
    write_results,
)
from ignis_wo.evaluation.jobs import JobBudget  # noqa: E402
from ignis_wo.evaluation.maintie import load_verified_splits  # noqa: E402
from ignis_wo.extraction.adapters import LiveAdapter  # noqa: E402
from ignis_wo.hosted.pacing import RequestPacer  # noqa: E402
from ignis_wo.hosted.prompts import ExtractionPrompt, select_examples  # noqa: E402
from ignis_wo.hosted.providers import client_from_environment  # noqa: E402


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=ROOT / "data" / "maintie" / "gold_release.json")
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--model", default=os.environ.get("MODEL_NAME"))
    parser.add_argument("--prompt", choices=["instruction", "fewshot"], default="instruction")
    parser.add_argument("--examples", type=int, default=5, help="few-shot examples taken from the train split")
    parser.add_argument("--output-mode", choices=["json_object", "json_schema"], default="json_object")
    parser.add_argument("--reasoning-effort", default="low", help="'default' omits the parameter")
    parser.add_argument("--max-tokens", type=int, default=4096, help="0 leaves max_tokens out (server default)")
    parser.add_argument("--budget-fallback", action="store_true",
                        help="retry once without max_tokens when the model rejects the budget")
    parser.add_argument("--allowance-reserve", type=float, default=0.25,
                        help="stop before the shared daily allowance falls below this fraction")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--requests-per-minute", type=float, default=20)
    parser.add_argument("--max-duration", type=float, default=600, help="seconds before remaining cases are skipped")
    parser.add_argument("--max-attempts", type=int, default=40, help="HTTP attempts per job, retries included")
    parser.add_argument("--final", action="store_true", help="required for the single test-split run")
    parser.add_argument("--ledger", type=Path, default=ROOT / TEST_LEDGER)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "benchmarks")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if not arguments.model:
        raise SystemExit("set MODEL_NAME in .env or pass --model")
    if arguments.split == "test" and not arguments.final:
        raise SystemExit("the test split is locked; pass --final only after the configuration is frozen on dev")
    needed = arguments.limit + 10
    if arguments.final and arguments.max_attempts < needed:
        raise SystemExit(f"the single test run must not stop part way: pass --max-attempts {needed} or more")
    splits = load_verified_splits(arguments.gold)
    items = splits[arguments.split][arguments.offset:arguments.offset + arguments.limit]
    examples = select_examples(splits["train"], arguments.examples) if arguments.prompt == "fewshot" else []
    reasoning_effort = None if arguments.reasoning_effort == "default" else arguments.reasoning_effort
    max_tokens = arguments.max_tokens or None
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    run_name = f"{stamp}-{arguments.split}-{re.sub(r'[^A-Za-z0-9.-]', '_', arguments.model)}"
    run_directory = arguments.out / run_name

    pacer = RequestPacer(arguments.requests_per_minute, arguments.concurrency, arguments.allowance_reserve)
    client = client_from_environment(pacer=pacer)
    job = JobBudget(run_name, arguments.max_attempts, arguments.max_duration)
    client.gateway.budget = job
    adapter = LiveAdapter(client, arguments.model, ExtractionPrompt(examples), arguments.output_mode, reasoning_effort,
                          max_tokens, run_directory / "replay.jsonl", budget_fallback=arguments.budget_fallback)
    if arguments.split == "test" and already_scored(arguments.ledger, adapter):
        raise SystemExit("test split refused: this model configuration was already scored")
    run_directory.mkdir(parents=True, exist_ok=True)

    cases = extraction_cases(items)
    rows, wall_seconds = run_cases(cases, extraction_call(adapter), arguments.concurrency, arguments.max_duration)
    summary = summarize(rows, wall_seconds)
    summary["scores"] = extraction_scores(cases, rows)
    summary["configuration"] = {
        "model_id": adapter.model_id, "model_version": adapter.model_version, "prompt_id": adapter.prompt.prompt_id,
        "output_mode": arguments.output_mode, "reasoning_effort": reasoning_effort, "max_tokens": max_tokens,
        "budget_fallback": arguments.budget_fallback, "concurrency": arguments.concurrency,
        "requests_per_minute_cap": arguments.requests_per_minute, "allowance_reserve": arguments.allowance_reserve,
        "base_url": client.base_url,
    }
    summary["data"] = {"split": arguments.split, "offset": arguments.offset, "items": len(items),
                       "source": "MaintIE gold_release.json, split verified against maintie_split_lock.json"}
    summary["job"] = job.write(run_directory / "job")
    write_results(run_directory, rows, summary)
    if arguments.split == "test":
        arguments.ledger.parent.mkdir(parents=True, exist_ok=True)
        with arguments.ledger.open("a", encoding="utf-8") as file:
            entry = {**summary["configuration"], "run": run_name, "complete": run_complete(summary)}
            file.write(json.dumps(entry) + "\n")
        if not entry["complete"]:
            print("test run incomplete (skipped cases or provider failures): logged, not locked; rerun when stable")
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"results: {run_directory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
