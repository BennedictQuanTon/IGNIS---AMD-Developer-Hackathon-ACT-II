"""Command line: `python -m ignis_wo run ...` for the pipeline, `python -m ignis_wo eval ...` for scoring."""

import argparse
import json
import os
import sys
from pathlib import Path

from ignis_wo.artifacts import StageFailed
from ignis_wo.contracts import ComponentCriticality
from ignis_wo.evaluation.maintie import load_gold, load_verified_splits
from ignis_wo.evaluation.scorer import score_items
from ignis_wo.extraction.adapters import FixtureAdapter, LiveAdapter, ReplayAdapter
from ignis_wo.pipeline import RunOptions, run_pipeline

DEFAULT_GOLD = Path("data/maintie/gold_release.json")
DEFAULT_LEDGER = Path("outputs/eval_ledger.jsonl")


def read_json(path: Path | None):
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def make_adapter(arguments):
    if arguments.mode == "fixture":
        return FixtureAdapter(load_gold(arguments.gold))
    if arguments.mode == "replay":
        return ReplayAdapter(arguments.replay, arguments.model_id, arguments.model_version)
    base_url = arguments.base_url or os.environ.get("MODEL_BASE_URL")
    if not base_url:
        raise SystemExit("live mode needs --base-url or MODEL_BASE_URL")
    api_key = os.environ.get("MODEL_API_KEY")
    return LiveAdapter(base_url, arguments.model_id, arguments.model_version, api_key, arguments.record)


def add_adapter_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mode", choices=["fixture", "replay", "live"], default="fixture")
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD, help="MaintIE-format gold file: fixture outputs and eval labels")
    parser.add_argument("--replay", type=Path, help="recorded JSONL responses for replay mode")
    parser.add_argument("--model-id", default=os.environ.get("MODEL_NAME", "maintie-lora"))
    parser.add_argument("--model-version", default="unversioned")
    parser.add_argument("--base-url", help="OpenAI-compatible endpoint for live mode; the key comes from MODEL_API_KEY")
    parser.add_argument("--record", type=Path, help="append live responses to this replay file")


def command_run(arguments) -> int:
    ratings = read_json(arguments.criticality) or []
    options = RunOptions(
        input_path=arguments.input,
        output_directory=arguments.out,
        adapter=make_adapter(arguments),
        reviewer=arguments.reviewer,
        synthetic=arguments.synthetic,
        allow_rejected=arguments.allow_rejected,
        mapping_overrides=read_json(arguments.mapping),
        decisions=read_json(arguments.decisions),
        criticalities=[ComponentCriticality.model_validate(rating) for rating in ratings],
    )
    try:
        summary = run_pipeline(options)
    except StageFailed as failure:
        print(f"FAILED at stage {failure.stage}; see {arguments.out / 'manifest.json'}", file=sys.stderr)
        for error in failure.errors[:10]:
            print(f"  {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2))
    return 0


def already_scored(ledger: Path, model_version: str) -> bool:
    if not ledger.exists():
        return False
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if line.strip() and json.loads(line).get("model_version") == model_version:
            return True
    return False


def command_eval(arguments) -> int:
    if arguments.split == "test" and not arguments.final:
        raise SystemExit("the test split is locked; pass --final for the single recorded final evaluation")
    adapter = make_adapter(arguments)
    if arguments.split == "test":
        if adapter.mode == "fixture" or already_scored(arguments.ledger, adapter.model_version):
            raise SystemExit("test split refused: fixture mode or this model version was already scored")
    splits = load_verified_splits(arguments.gold)
    result = score_items(splits[arguments.split], adapter, arguments.depth, arguments.perturb)
    result.update(
        {
            "split": arguments.split,
            "adapter_mode": adapter.mode,
            "model_id": adapter.model_id,
            "model_version": adapter.model_version,
            "perturbed": arguments.perturb,
            "data": "maintie gold_release.json, split verified against maintie_split_lock.json",
        }
    )
    print(json.dumps(result, indent=2))
    if arguments.split == "test":
        arguments.ledger.parent.mkdir(parents=True, exist_ok=True)
        with arguments.ledger.open("a", encoding="utf-8") as file:
            file.write(json.dumps(result) + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ignis_wo")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="run the full pipeline on one export file")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--reviewer", default="demo-script")
    run.add_argument("--synthetic", action="store_true", help="label every output as synthetic data")
    run.add_argument("--allow-rejected", action="store_true", help="continue when some outputs fail validation")
    run.add_argument("--mapping", type=Path, help="JSON of field to column overrides")
    run.add_argument("--decisions", type=Path, help="JSON review decisions keyed by record id")
    run.add_argument("--criticality", type=Path, help="JSON list of component criticality ratings")
    add_adapter_arguments(run)
    run.set_defaults(handler=command_run)

    evaluate = commands.add_parser("eval", help="score extraction on a MaintIE split")
    evaluate.add_argument("--split", choices=["train", "dev", "test"], default="dev")
    evaluate.add_argument("--depth", type=int, help="truncate entity types to this many levels")
    evaluate.add_argument("--perturb", action="store_true", help="inject known errors to test the scorer")
    evaluate.add_argument("--final", action="store_true", help="required for the one-time test split run")
    evaluate.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    add_adapter_arguments(evaluate)
    evaluate.set_defaults(handler=command_eval)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    return arguments.handler(arguments)


if __name__ == "__main__":
    sys.exit(main())
