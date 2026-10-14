"""MaintIE splits as published upstream, verified against a committed hash lock.

Upstream `models/create_datasets.py` shuffles the original list but slices the unshuffled copy,
so the published split is positional: the first 80% is train, the next 10% dev, the rest test.
"""

import json
from pathlib import Path

from ignis_wo.hashing import sha256_text

LOCK_PATH = Path(__file__).with_name("maintie_split_lock.json")
SPLIT_NAMES = ("train", "dev", "test")


def load_gold(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def split_items(items: list) -> dict[str, list]:
    train_end = int(0.8 * len(items))
    dev_end = int(0.9 * len(items))
    return {"train": items[:train_end], "dev": items[train_end:dev_end], "test": items[dev_end:]}


def split_hash(items: list[dict]) -> str:
    texts = [" ".join(item["tokens"]) for item in items]
    return sha256_text("\n".join(texts))


def verify_split(splits: dict[str, list[dict]], lock_path: Path = LOCK_PATH) -> None:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    for name in SPLIT_NAMES:
        expected = lock["splits"][name]
        actual_size = len(splits[name])
        actual_hash = split_hash(splits[name])
        if actual_size != expected["size"] or actual_hash != expected["sha256"]:
            raise ValueError(f"MaintIE {name} split does not match the lock; the data or split logic changed")


def load_verified_splits(gold_path: Path) -> dict[str, list[dict]]:
    splits = split_items(load_gold(gold_path))
    verify_split(splits)
    return splits
