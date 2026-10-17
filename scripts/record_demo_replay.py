"""Record the demo replay package: one synthetic pump run through live hosted extraction and explanation,
then replay it offline and check that suggestions and draft come back identical.

Run with: uv run --env-file .env --no-project --with-requirements requirements-dev.txt python scripts/record_demo_replay.py
Needs MODEL_NAME (frozen extraction), EXPLANATION_MODEL_NAME and MaintIE from scripts/fetch_maintie.py.
Rehearse the result with: python scripts/serve_hosted.py --replay-dir docs/benchmarks/replay
--extraction-replay reuses a recorded extraction (and the OCR replies beside it), so only the explanation goes live
and the demo keeps the same records. A draft that does not reach pending_expert_review is refused.
The job stops at 40 HTTP attempts or 30 minutes, and while 25% of the daily allowance remains.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.evaluation.jobs import JobBudget  # noqa: E402
from ignis_wo.hosted.explanation import HostedExplanationProvider  # noqa: E402
from ignis_wo.hosted.frozen import frozen_extraction_adapter, load_train_items  # noqa: E402
from ignis_wo.hosted.pacing import RequestPacer  # noqa: E402
from ignis_wo.hosted.providers import (  # noqa: E402
    client_from_environment,
    extraction_provider_for,
    replay_providers,
)
from ignis_wo.workflow.service import Workflow  # noqa: E402

DESCRIPTIONS = ["pump seal leaking", "mechanical seal leak at gland", "seal leaking again after restart",
                "flush line blocked and seal leaking", "pump seal leak observed on night shift", "seal weeping at pump"]
HEADER = "WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h),Data note\n"


def demo_csv() -> str:
    rows = [f"WO-SYN-{index:02d},PUMP-SYN-01,2025-01-{index:02d},{text},{index / 2:.1f},SYNTHETIC fields"
            for index, text in enumerate(DESCRIPTIONS, 1)]
    return HEADER + "\n".join(rows) + "\n"


def run_demo(directory: Path, extraction_provider, explanation_provider) -> dict:
    workflow = Workflow(directory / "state.sqlite3", directory, extraction_provider=extraction_provider,
                        explanation_provider=explanation_provider)
    run = workflow.create_run("Synthetic pump replay package", "synthetic-demo-operator", True, "injected")
    state = workflow.upload(run["run_id"], run["revision"], "synthetic-pump.csv", demo_csv())
    state = workflow.confirm_mapping(run["run_id"], state["revision"], state["proposal"]["mapping"], "synthetic headers")
    state = workflow.extract(run["run_id"], state["revision"])
    if state["stage_status"].get("extraction") != "succeeded":
        raise SystemExit(f"extraction did not succeed: {state.get('stage_errors')}")
    usable = {suggestion["record_id"] for suggestion in state["suggestions"] if suggestion["output"]}
    for record in state["records"]:
        decision = "accepted" if record["record_id"] in usable else "rejected"
        state = workflow.review(run["run_id"], state["revision"], record["record_id"], decision,
                                f"SYNTHETIC replay package: {decision} without human review",
                                reviewer="SYNTHETIC DEMO SIMULATOR")
    criticality = [{"component": "seal", "value": 3, "reason": "Synthetic demo policy value", "set_by": "synthetic"}]
    state = workflow.analyze(run["run_id"], state["revision"], criticality)
    state = workflow.build_context(run["run_id"], state["revision"], "PUMP-SYN-01", "seal", "seal leakage flush")
    state = workflow.generate_context_draft(run["run_id"], state["revision"])
    labels = [[entity["type"] for entity in (suggestion.get("output") or {}).get("entities", [])]
              for suggestion in state["suggestions"]]
    return {"labels": labels, "draft_result": state["draft_result"], "context_status": state["context"]["status"]}


def extraction_for(arguments, client):
    if arguments.extraction_replay is None:
        adapter = frozen_extraction_adapter(client, os.environ["MODEL_NAME"], load_train_items(),
                                            arguments.out / "extraction-replay.jsonl")
        return extraction_provider_for(adapter, 25)
    shutil.copyfile(arguments.extraction_replay, arguments.out / "extraction-replay.jsonl")
    ocr_replies = arguments.extraction_replay.parent / "ocr-replay.jsonl"
    if ocr_replies.exists():
        shutil.copyfile(ocr_replies, arguments.out / "ocr-replay.jsonl")
    extraction, _ = replay_providers(arguments.out)
    return extraction


def record(arguments, client) -> dict:
    extraction = extraction_for(arguments, client)
    explanation = HostedExplanationProvider(client, arguments.explanation_model, budget_fallback=True,
                                            record_path=arguments.out / "explanation-replay.jsonl",
                                            prompt_version=arguments.prompt_version)
    with tempfile.TemporaryDirectory() as directory:
        live = run_demo(Path(directory), extraction, explanation)
    status = live["draft_result"]["status"]
    if status != "pending_expert_review":
        raise SystemExit(f"the live draft is {status}, not pending_expert_review; this package cannot serve the demo")
    return {**live, "extraction_model": extraction.model_id, "explanation_prompt_id": explanation.prompt_id}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "benchmarks" / "replay")
    parser.add_argument("--explanation-model", default=os.environ.get("EXPLANATION_MODEL_NAME"))
    parser.add_argument("--prompt-version", choices=["v1", "v2", "v3"], default="v3")
    parser.add_argument("--allowance-reserve", type=float, default=0.25)
    parser.add_argument("--extraction-replay", type=Path, help="reuse this extraction recording instead of a live run")
    arguments = parser.parse_args()
    if not arguments.explanation_model:
        raise SystemExit("set EXPLANATION_MODEL_NAME (or --explanation-model)")
    if arguments.extraction_replay is None and not os.environ.get("MODEL_NAME"):
        raise SystemExit("set MODEL_NAME, or pass --extraction-replay to reuse a recorded extraction")
    if any(arguments.out.glob("*-replay.jsonl")):
        raise SystemExit(f"{arguments.out} already holds recordings; move them before recording a new package")
    arguments.out.mkdir(parents=True, exist_ok=True)
    job = JobBudget("demo-replay", 40, 1800)
    client = client_from_environment(pacer=RequestPacer(20, 1, arguments.allowance_reserve))
    client.gateway.budget = job
    live = record(arguments, client)
    with tempfile.TemporaryDirectory() as directory:
        replayed = run_demo(Path(directory), *replay_providers(arguments.out))
    matches = {"labels": live["labels"] == replayed["labels"],
               "draft": live["draft_result"].get("draft") == replayed["draft_result"].get("draft")}
    summary = {"job": job.summary(), "live_draft_status": live["draft_result"]["status"],
               "context_status": live["context_status"], "replay_matches": matches,
               "explanation_model": arguments.explanation_model, "explanation_prompt_id": live["explanation_prompt_id"],
               "extraction_model": live["extraction_model"],
               "extraction_source": "live" if arguments.extraction_replay is None else "recording reused from "
               + arguments.extraction_replay.as_posix()}
    (arguments.out / "demo_input.csv").write_text(demo_csv(), encoding="utf-8", newline="\n")
    (arguments.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))
    return 0 if all(matches.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
