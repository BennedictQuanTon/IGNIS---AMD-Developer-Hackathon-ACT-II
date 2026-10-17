"""Build the #23 handoff under docs/benchmarks/ from the recorded jobs in outputs/benchmarks/23/.

Run with: uv run --no-project --with-requirements requirements-dev.txt python scripts/report_benchmarks.py --extraction-runs <run dir> <run dir>
Writes results.json (every number the docs cite), SVG charts, the frozen manifest and the blind rating
sheet. The rating key stays in outputs/ so raters cannot see model names. No API call is made.
"""

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.evaluation.charts import grouped_bars  # noqa: E402
from ignis_wo.evaluation.explanation_benchmark import load_scenarios, write_blind_sheet  # noqa: E402
from ignis_wo.evaluation.reader_benchmark import FAMILIES  # noqa: E402
from ignis_wo.hosted.frozen import load_frozen_config  # noqa: E402

RUNS = ROOT / "outputs" / "benchmarks" / "23"
DOCS = ROOT / "docs" / "benchmarks"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def reader_results() -> dict:
    results = {}
    for reader in ("native", "mineru"):
        directory = RUNS / "reader-pilot" / f"read-{reader}"
        rows = [row for row in read_rows(directory / "first.jsonl") if "error" not in row]
        families = {}
        for name in FAMILIES:
            pages = [row for row in rows if row["family"] == name]
            if not pages:
                continue
            critical = sum(len(row["critical_found"]) for row in pages)
            critical_total = critical + sum(len(row["critical_missing"]) for row in pages)
            families[name] = {"split": pages[0]["split"], "pages": len(pages), "cer_mean": mean([row["cer"] for row in pages]),
                              "wer_mean": mean([row["wer"] for row in pages]),
                              "critical_found": critical, "critical_total": critical_total,
                              "numbers_missing": sorted({number for row in pages for number in row["numbers_missing"]}),
                              "table_rows_correct": sum(row["table_rows_correct"] for row in pages),
                              "table_rows": sum(row["table_rows"] for row in pages),
                              "latency_seconds": [row["latency_seconds"] for row in pages]}
        summary = read_json(directory / "summary.json")
        results[reader] = {"families": families, "job": summary["job"], "repeat_modes": summary["repeat_modes"]}
    return results


def explanation_results() -> dict:
    results = {}
    for directory in sorted((RUNS / "explanation").iterdir()):
        if (directory / "summary.json").exists():
            summary = read_json(directory / "summary.json")
            results[directory.name] = {key: summary.get(key) for key in ("stage", "concurrency", "models", "runtime", "job")}
    return results


def extraction_results(run_directories: list[Path]) -> dict:
    results = {}
    for directory in run_directories:
        summary = read_json(directory / "summary.json")
        keys = ("attempted", "valid", "outcomes", "latency_p50_seconds", "latency_p95_seconds", "wall_seconds",
                "valid_per_minute", "attempted_per_minute", "scores", "configuration", "job")
        results[directory.name] = {key: summary.get(key) for key in keys}
    return results


def percent(rate: dict) -> float | None:
    return round(100 * rate["true"] / rate["n"], 1) if rate and rate["n"] else None


def charts(results: dict) -> dict[str, str]:
    readers = results["readers"]
    names = list(FAMILIES)
    cer = {reader.replace("mineru", "MinerU2.5-Pro").replace("native", "Native (pypdf)"):
           [readers[reader]["families"].get(name, {}).get("cer_mean") for name in names] for reader in readers}
    critical = {}
    for reader, label in (("native", "Native (pypdf)"), ("mineru", "MinerU2.5-Pro")):
        column = []
        for name in names:
            family = readers[reader]["families"].get(name)
            column.append(round(100 * family["critical_found"] / family["critical_total"], 1) if family else None)
        critical[label] = column
    short = [name.split("-", 1)[1] for name in names]
    output = {"reader-cer.svg": grouped_bars("Reader character error rate per family (lower is better)", short, cer,
                                             note="2 pages per family; synthetic generated pages; n/a = reader not applicable"),
              "reader-critical-fields.svg": grouped_bars("Critical fields read exactly (% of IDs, values, negations)", short,
                                                         critical, "%", 100, note="2 pages per family; synthetic pages")}
    dev = {name: run for name, run in results["explanation"].items() if run["stage"] == "dev"}
    if dev:
        metrics = [("first_pass_valid", "First-pass valid"), ("valid_after_repair", "Valid after repair"),
                   ("outcome_correct", "Support/abstain right"), ("support_hit", "Cites expected passage")]
        series = {}
        for run in dev.values():
            for model, summary in run["models"].items():
                series[model] = [percent(summary[key]) for key, _ in metrics]
        output["explanation-dev-quality.svg"] = grouped_bars(
            "Explanation on 12 dev scenarios (synthetic, drafted by Yoshio)", [label for _, label in metrics], series,
            "%", 100, note="n = 12 each; Qwen's 2 timeouts are absent from the last two bars; validity counts the no-digits rule")
        latency = {model: [summary["model_seconds_p50"], summary["model_seconds_p95"]]
                   for run in dev.values() for model, summary in run["models"].items()}
        output["explanation-dev-latency.svg"] = grouped_bars("Explanation model time per scenario, dev (seconds)",
                                                             ["p50", "p95"], latency, " s",
                                                             note="Includes repair calls; n = 12 per model; preliminary tails")
    extraction = sorted(results["extraction"].values(), key=lambda run: run["configuration"]["concurrency"])
    explanation = results["explanation"]
    explanation_rates = [explanation.get("dev-DeepSeek-V4-Flash", {}).get("runtime", {}).get("valid_per_minute"),
                         explanation.get("runtime-DeepSeek-V4-Flash-c2", {}).get("runtime", {}).get("valid_per_minute")]
    if len(extraction) == 2:
        output["throughput.svg"] = grouped_bars(
            "Valid outputs per minute by concurrency (shared 20 RPM key)", ["concurrency 1", "concurrency 2"],
            {"Extraction (Vision-Exp, 20 dev records)": [run["valid_per_minute"] for run in extraction],
             "Explanation (DeepSeek-V4-Flash)": explanation_rates},
            note="Explanation c1 = 12 dev scenarios, c2 = 20 dev tasks; validity includes the no-digits rule")
    return output


def manifest(results: dict) -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip()
    pilot = read_json(RUNS / "reader-pilot" / "lock.json")
    lock = read_json(DOCS / "scenarios" / "scenario_lock.json")
    frozen = load_frozen_config()
    return {"issue": "#23", "built_at": datetime.datetime.now(datetime.UTC).isoformat(), "client_commit": commit,
            "reader_pilot": {"files": pilot["files"], "gold_hash": pilot["gold_hash"],
                             "rights": "generated synthetic pages; no third-party documents"},
            "scenarios": {"sha256": lock["sha256"], "dev": lock["dev"], "heldout": lock["heldout"],
                          "status": "drafted by Yoshio, pending Tuong review"},
            "extraction": {key: frozen[key] for key in ("model_id", "model_version", "prompt_id", "max_tokens")},
            "explanation_settings": {"reasoning_effort": "low", "max_tokens": 4096, "budget_fallback": True,
                                     "output_mode": "json_object", "repair_attempts": 1},
            "reader": {"model_id": "MinerU2.5-Pro", "endpoint": "/ocr", "parser_version": "document-parse-v1"},
            "limitations": ["Provider model weights and serving versions are not exposed; identities are API names.",
                            "Single runs on small synthetic sets; p95 values from n <= 20 are preliminary.",
                            "Quota snapshots come from shared-key headers that may lag and include teammates."],
            "jobs": {"readers": {reader: data["job"] for reader, data in results["readers"].items()},
                     "explanation": {name: run["job"] for name, run in results["explanation"].items()}}}


def blind_sheet() -> int:
    families = {family["family_id"]: family for family in load_scenarios()}
    rows = []
    for directory in (RUNS / "explanation").iterdir():
        if directory.name.startswith(("dev-", "heldout-")):
            rows.extend(read_rows(directory / "rows.jsonl"))
    return write_blind_sheet(rows, families, DOCS / "rating" / "blind_sheet.csv", RUNS / "blind_key.json", seed=23)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--extraction-runs", type=Path, nargs="*", default=[])
    arguments = parser.parse_args()
    results = {"readers": reader_results(), "explanation": explanation_results(),
               "extraction": extraction_results(arguments.extraction_runs),
               "stage0": read_json(RUNS / "stage0" / "summary.json")}
    (DOCS / "charts").mkdir(parents=True, exist_ok=True)
    for name, svg in charts(results).items():
        (DOCS / "charts" / name).write_text(svg, encoding="utf-8", newline="\n")
    (DOCS / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (DOCS / "manifest.json").write_text(json.dumps(manifest(results), indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"charts": sorted(charts(results)), "blind_rows": blind_sheet()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
