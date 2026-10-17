"""Audit frozen synthetic scenarios locally. This does not approve labels or score model quality."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pydantic import ValidationError  # noqa: E402
from ignis_wo.contracts import FactRow  # noqa: E402
from ignis_wo.evaluation.explanation_benchmark import load_scenarios, scenario_lock, scenario_pack  # noqa: E402


def audit():
    rows = []
    for family in load_scenarios():
        context = scenario_pack(family)
        pack = context.get("pack") or {}
        retrieved = {item["passage_id"] for item in pack.get("passages", [])}
        expected = family["expected"]
        findings = []
        if expected["outcome"] == "support" and not retrieved.intersection(expected["supporting_passages"]):
            findings.append("Expected supporting passage is absent from retrieval.")
        for fact in family["facts"]:
            try:
                FactRow.model_validate(fact)
            except ValidationError as error:
                fields = sorted({".".join(map(str, item["loc"])) for item in error.errors()})
                findings.append(f"Benchmark fact {fact['fact_id']} differs from runtime FactRow: {', '.join(fields)}")
        model = family["graph"]["assets"][family["asset_id"]]["model"]
        wrong = {item["passage_id"] for item in family["corpus"]["documents"] if item["asset_model"] != model}
        if wrong & retrieved:
            findings.append("Wrong-model evidence entered the pack.")
        rows.append({"family_id": family["family_id"], "split": family["split"], "trap": family["trap"],
                     "expected": expected, "retrieved": sorted(retrieved), "context_status": context["status"],
                     "findings": findings, "human_semantic_review": "pending"})
    return {"scope": "technical audit of frozen synthetic scenario definitions; zero model calls",
            "scenario_lock": scenario_lock(), "live_calls": 0, "human_approval": False, "rows": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "scenario-audit.json")
    args = parser.parse_args()
    result = audit()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scenarios": len(result["rows"]), "with_findings": sum(bool(row["findings"]) for row in result["rows"]),
                      "human_approval": False, "live_calls": 0, "output": str(args.out)}, indent=2))
