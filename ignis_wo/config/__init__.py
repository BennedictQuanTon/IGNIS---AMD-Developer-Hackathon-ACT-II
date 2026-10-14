"""Versioned configuration tables shipped with the package."""

import json
from functools import cache
from pathlib import Path

CONFIG_DIRECTORY = Path(__file__).parent


@cache
def load_config(name: str) -> dict:
    path = CONFIG_DIRECTORY / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def entity_labels() -> frozenset[str]:
    return frozenset(load_config("maintie_labels_v1")["entity_types"])


def relation_labels() -> frozenset[str]:
    return frozenset(load_config("maintie_labels_v1")["relation_types"])
