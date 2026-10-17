"""Builds runtime extraction from the frozen configuration in extraction_config.json.

The few-shot examples come from the verified MaintIE train split, which stays in the ignored
`data/` folder. Both the current and the legacy prompt hash are checked, so the running app uses
exactly the configuration that was scored.
"""

import json
import sys
from pathlib import Path

from ignis_wo.evaluation.maintie import load_verified_splits
from ignis_wo.extraction.adapters import LiveAdapter
from ignis_wo.hosted.prompts import ExtractionPrompt, select_examples

CONFIG_PATH = Path(__file__).with_name("extraction_config.json")
DEFAULT_GOLD = Path(__file__).resolve().parents[2] / "data" / "maintie" / "gold_release.json"


def load_frozen_config(path: Path = CONFIG_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_train_items(gold_path: Path = DEFAULT_GOLD) -> list[dict]:
    if not gold_path.exists():
        raise SystemExit(f"{gold_path} is missing; the frozen extraction prompt needs MaintIE train examples. "
                         "Run scripts/fetch_maintie.py first.")
    return load_verified_splits(gold_path)["train"]


def frozen_extraction_adapter(client, model_id: str, train_items: list[dict], record_path: Path | None = None,
                              config: dict | None = None) -> LiveAdapter:
    config = config or load_frozen_config()
    prompt = ExtractionPrompt(select_examples(train_items, config["example_count"]))
    expected = {"prompt_id": config["prompt_id"], "legacy prompt_id": config["scored_as"]["prompt_id"]}
    built = {"prompt_id": prompt.prompt_id, "legacy prompt_id": prompt.legacy_prompt_id()}
    if built != expected:
        raise SystemExit(f"few-shot examples do not match the frozen configuration: built {built}, expected {expected}")
    adapter = LiveAdapter(client, model_id, prompt, config["output_mode"], config["reasoning_effort"],
                          config["max_tokens"], record_path, budget_fallback=config["budget_fallback"])
    adapter.scored_configuration = model_id == config["model_id"]
    if not adapter.scored_configuration:
        print(f"note: extraction model {model_id} with the frozen prompt is not the scored configuration "
              f"({config['model_id']})", file=sys.stderr)
    return adapter
