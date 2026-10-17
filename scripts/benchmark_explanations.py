"""#23 Stage 2 and 3: explanation models on the locked synthetic pump scenarios.

Run with: uv run --env-file .env --no-project --with-requirements requirements-dev.txt python scripts/benchmark_explanations.py <stage>
Stages: dev, heldout (runs once), repeat (5 dev cases x 3), runtime (20 dev tasks at --concurrency),
ablation (gold text vs OCR text on 4 reader-pilot pages; needs the mineru reader run first).
Each job stops at 40 HTTP attempts or 30 minutes, and while 25% of the daily allowance remains, so run
one model per job when repairs could push a stage past 40 attempts. The blind rating sheet is built by
scripts/report_benchmarks.py from all dev and held-out rows, so model names are mixed across jobs.
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.evaluation.benchmark import percentile, run_cases  # noqa: E402
from ignis_wo.evaluation.explanation_benchmark import (  # noqa: E402
    load_scenarios,
    run_family,
    scenario_pack,
    scored_row,
    summarize_model,
)
from ignis_wo.evaluation.jobs import JobBudget  # noqa: E402
from ignis_wo.evaluation.reader_benchmark import FAMILIES  # noqa: E402
from ignis_wo.extraction.adapters import ReplayMiss  # noqa: E402
from ignis_wo.hosted.explanation import HostedExplanationProvider  # noqa: E402
from ignis_wo.hosted.pacing import RequestPacer  # noqa: E402
from ignis_wo.hosted.providers import client_from_environment  # noqa: E402

RESULTS = ROOT / "outputs" / "benchmarks" / "23" / "explanation"
PILOT = ROOT / "outputs" / "benchmarks" / "23" / "reader-pilot"
REPEAT_FAMILIES = ["S01", "S02", "S03", "S08", "S10"]
ABLATION_PAGES = [("F1-manual", 0, "seal flush supply inspection"), ("F3-clean-scan", 0, "seal leakage flush"),
                  ("F3-clean-scan", 1, "seal leakage flush supply"), ("F4-noisy-scan", 0, "seal chamber leak")]


def providers(arguments, job: JobBudget, directory: Path) -> list[HostedExplanationProvider]:
    pacer = RequestPacer(20, arguments.concurrency, arguments.allowance_reserve)
    client = client_from_environment(pacer=pacer)
    client.gateway.budget = job
    return [HostedExplanationProvider(client, model, reasoning_effort="low", max_tokens=4096, budget_fallback=True,
                                      record_path=directory / f"{model}-replay.jsonl") for model in arguments.models]


def ablation_families() -> list[dict]:
    """Single-passage cases whose text is the gold page or the raw MinerU output of the same page."""
    families = []
    for family_name, page_number, query in ABLATION_PAGES:
        stem = f"{family_name}.pdf" if FAMILIES[family_name]["kind"] == "pdf" else f"{family_name}-p{page_number}.png"
        document_id = stem.rsplit(".", 1)[0]
        artifact_path = next((PILOT / "read-mineru" / "documents" / document_id).glob("r1/*/artifact.json"))
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        ocr_page = artifact["pages"][page_number if stem.endswith(".pdf") else 0]["markdown"]
        gold_page = " ".join(FAMILIES[family_name]["pages"][page_number]["lines"])
        for variant, text in (("gold", gold_page), ("ocr", ocr_page)):
            families.append(ablation_family(f"A-{document_id}-{page_number}-{variant}", query, text))
    return families


def ablation_family(family_id: str, query: str, text: str) -> dict:
    passage = {"document_id": family_id, "passage_id": family_id, "version": "1", "asset_model": "PX-100",
               "component": "seal", "status": "approved", "reviewer": "SYNTHETIC ablation", "source_id": family_id,
               "location": "reader pilot page", "text": text}
    fact = {"fact_id": f"F-{family_id}", "snapshot_id": f"S-{family_id}", "kind": "recurrence",
            "scope": {"component": "seal"}, "value": 2, "unit": "work_orders", "status": "computed",
            "record_ids": [f"WO-{family_id}"]}
    return {"family_id": family_id, "split": "ablation", "trap": "ocr_vs_gold", "asset_id": "PUMP-ABL",
            "component": "seal", "query": query, "snapshot_id": f"S-{family_id}", "facts": [fact],
            "corpus": {"corpus_version": family_id, "synthetic": True, "documents": [passage]},
            "graph": {"graph_version": "ablation", "assets": {"PUMP-ABL": {"model": "PX-100",
                                                                          "components": {"seal": [family_id]}}}},
            "expected": {"outcome": "support", "supporting_passages": [family_id], "distractor_passages": []}}


def stage_families(stage: str) -> list[dict]:
    if stage == "heldout":
        return load_scenarios("heldout")
    if stage == "ablation":
        return ablation_families()
    dev = load_scenarios("dev")
    if stage == "repeat":
        chosen = [family for family in dev if family["family_id"] in REPEAT_FAMILIES]
        return [family for family in chosen for _ in range(3)]
    if stage == "runtime":
        return [dev[index % len(dev)] for index in range(20)]
    return dev


def runtime_summary(rows: list[dict], wall_seconds: float) -> dict:
    minutes = wall_seconds / 60 if wall_seconds else None
    finished = [row for row in rows if row.get("status") != "skipped"]
    waits = [row["wall_seconds"] - row.get("model_seconds", 0) for row in finished if "wall_seconds" in row]
    return {"tasks": len(rows), "finished": len(finished), "wall_seconds": round(wall_seconds, 1),
            "calls": sum(row.get("calls", 0) for row in finished),
            "calls_per_minute": round(sum(row.get("calls", 0) for row in finished) / minutes, 2) if minutes else None,
            "valid_per_minute": round(sum(bool(row.get("valid")) for row in finished) / minutes, 2) if minutes else None,
            "full_path_p50": percentile([row["wall_seconds"] for row in finished], 50),
            "full_path_p95": percentile([row["wall_seconds"] for row in finished], 95),
            "queue_and_pacing_p50": percentile(waits, 50), "n": len(finished)}


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rescored_row(family: dict, provider, case_id: str, live: dict) -> dict:
    try:
        row = run_family(family, provider)
    except ReplayMiss as error:
        row = {**scored_row(family, provider.model_id, scenario_pack(family), None, []), "error": "not_recorded",
               "message": str(error)}
    return {**row, "case_id": case_id, "wall_seconds": live.get("wall_seconds"), "live_status": live.get("status", "ok")}


def rescore(arguments, directory: Path, families: list[dict]) -> int:
    """Re-scores a finished job from its recordings with no API call; live timings come from the job's rows."""
    live_path = directory / "rows.live.jsonl"
    if not live_path.exists():
        (directory / "rows.jsonl").replace(live_path)
    live_rows = {row["case_id"]: row for row in read_rows(live_path)}
    rows = []
    for model in arguments.models:
        provider = HostedExplanationProvider(None, model, reasoning_effort="low", max_tokens=4096, budget_fallback=True,
                                             replay_path=directory / f"{model}-replay.jsonl")
        for index, family in enumerate(families):
            case_id = f"{family['family_id']}:{model}:{index}"
            rows.append(rescored_row(family, provider, case_id, live_rows.get(case_id, {})))
    lines = [json.dumps(row, sort_keys=True) for row in rows]
    (directory / "rows.jsonl").write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    summary["models"] = {model: summarize_model([row for row in rows if row["model_id"] == model])
                         for model in arguments.models}
    summary["runtime"] = runtime_summary(rows, summary["runtime"]["wall_seconds"])
    summary["rescored_from_recordings"] = True
    (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("models", "runtime")}, indent=2))
    return 0


def main() -> int:
    arguments = parse_arguments()
    name = f"{arguments.stage}-{'+'.join(arguments.models)}"
    if arguments.stage == "runtime":
        name += f"-c{arguments.concurrency}"
    directory = RESULTS / name
    if arguments.rescore and arguments.stage in ("repeat", "runtime"):
        raise SystemExit("--rescore cannot separate repeated runs of one scenario; their live rows are the record")
    if arguments.rescore:
        return rescore(arguments, directory, stage_families(arguments.stage))
    if arguments.stage == "heldout" and (directory / "summary.json").exists():
        raise SystemExit("the held-out scenarios were already run once for these models; they are not re-run")
    directory.mkdir(parents=True, exist_ok=True)
    job = JobBudget(f"stage2-{name}", arguments.max_attempts, arguments.max_seconds)
    families = stage_families(arguments.stage)
    cases = [{"case_id": f"{family['family_id']}:{provider.model_id}:{index}", "family": family, "provider": provider}
             for provider in providers(arguments, job, directory) for index, family in enumerate(families)]
    started = time.monotonic()
    rows, wall_seconds = run_cases(cases, lambda case: run_family(case["family"], case["provider"]),
                                   arguments.concurrency, arguments.max_seconds)
    lines = [json.dumps(row, sort_keys=True) for row in rows]
    (directory / "rows.jsonl").write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    by_model = {model: summarize_model([row for row in rows if row.get("model_id") == model])
                for model in arguments.models}
    summary = {"stage": arguments.stage, "concurrency": arguments.concurrency, "models": by_model,
               "runtime": runtime_summary(rows, wall_seconds), "job": job.write(directory / "job"),
               "statuses": sorted({row.get("status", "ok") for row in rows}),
               "elapsed_seconds": round(time.monotonic() - started, 1)}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("models", "runtime", "job", "statuses")}, indent=2))
    return 0


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", choices=["dev", "heldout", "repeat", "runtime", "ablation"])
    parser.add_argument("--models", nargs="+", default=["DeepSeek-V4-Flash", "Qwen3.8-27B"])
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=40)
    parser.add_argument("--max-seconds", type=float, default=1800)
    parser.add_argument("--allowance-reserve", type=float, default=0.25)
    parser.add_argument("--rescore", action="store_true", help="re-score a finished job from its recordings, no calls")
    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
