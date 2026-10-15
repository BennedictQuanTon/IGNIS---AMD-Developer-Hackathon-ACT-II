"""Create a reproducible, local synthetic-pump API demo database and issued PDF."""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.workflow.service import Workflow  # noqa: E402


def fixture_explanation(pack):
    manual = next(p for p in pack["passages"] if p["document_id"] == "MAN-PUMP-A-v1")
    case = next((p for p in pack["passages"] if p["document_id"] == "CASE-PUMP-SEAL-01-v1"), manual)
    return {
        "pack_id": pack["pack_id"],
        "hypotheses": [{"text": "The synthetic work order describes seal leakage. The applicable procedure offers inspection guidance but does not establish a cause.", "citations": [manual["passage_id"]], "fact_bindings": []}],
        "alternatives": [{"text": "A separate synthetic case records reduced flush flow alongside a leak and explicitly does not establish causation.", "citations": [case["passage_id"]], "fact_bindings": []}],
        "uncertainty": "These synthetic references do not establish the cause of this work-order observation.",
        "inspection": {"text": "Check whether leakage is active and whether the flush line is obstructed.", "citations": [manual["passage_id"]], "fact_bindings": []},
        "abstain": False,
    }


fixture_explanation.model_id = "synthetic-fixture-explanation"
fixture_explanation.prompt_id = "synthetic-fixture-prompt-v1"
fixture_explanation.explanation_mode = "synthetic_fixture_simulation"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "outputs" / "demo-backend")
    parser.add_argument("--reset", action="store_true", help="delete and recreate only the selected outputs/demo-backend directory")
    args = parser.parse_args()
    target = args.data if args.data.is_absolute() else ROOT / args.data
    target = target.resolve()
    allowed = (ROOT / "outputs").resolve()
    if target == allowed or allowed not in target.parents:
        raise SystemExit(f"demo data path must be a child of {allowed}")
    if args.reset and target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    items = json.loads((ROOT / "tests" / "fixtures" / "maintie_sample.json").read_text(encoding="utf-8"))
    workflow = Workflow(target / "state.sqlite3", target, items, explanation_provider=fixture_explanation)
    run = workflow.create_run("Synthetic pump backend demo", "synthetic-demo-operator", True, "fixture")
    rid = run["run_id"]
    header = "WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h),Data note\n"
    rows = [f"WO-SYN-{index:02d},PUMP-SYN-01,2025-01-{index:02d},pump seal leaking,{index / 2:.1f},SYNTHETIC fields" for index in range(1, 13)]
    csv_text = header + "\n".join(rows) + "\n"
    uploaded = workflow.upload(rid, run["revision"], "synthetic-pump.csv", csv_text)
    mapped = workflow.confirm_mapping(rid, uploaded["revision"], uploaded["proposal"]["mapping"], "Synthetic fixture headers confirmed for demo")
    extracted = workflow.extract(rid, mapped["revision"])
    reviewed = extracted
    for record in extracted["records"]:
        reviewed = workflow.review(rid, reviewed["revision"], record["record_id"], "accepted", "Fixture extraction shown for workflow demonstration", reviewer="SYNTHETIC DEMO SIMULATOR", demo_auto_review=True)
    analyzed = workflow.analyze(rid, reviewed["revision"], [{"component": "seal", "value": 3, "reason": "Synthetic demo policy value", "set_by": "synthetic supervisor simulation"}])
    if not any(alert["type"] == "initial_high_notice" for alert in analyzed["alerts"]):
        raise SystemExit("seed expected an initial High notice from synthetic repeated seal work orders")
    context = workflow.build_context(rid, analyzed["revision"], "PUMP-SYN-01", "seal", "seal leakage flush")
    generated = workflow.generate_context_draft(rid, context["revision"])
    if generated["draft_result"]["status"] != "pending_expert_review":
        raise SystemExit("fixture explanation failed its schema checks: " + "; ".join(generated["draft_result"]["errors"]))
    signed = workflow.expert_review(rid, generated["revision"], "accepted", "SYNTHETIC DEMO SIGNOFF SIMULATOR", "SIMULATED signoff for a local workflow fixture; not a real expert decision")
    issued = workflow.issue_report(rid, signed["revision"])
    print(json.dumps({"run_id": rid, "revision": issued["revision"], "report": issued["latest_report"], "label": "SYNTHETIC FIXTURE / SIMULATED REVIEW AND SIGNOFF"}, indent=2))


if __name__ == "__main__":
    main()
