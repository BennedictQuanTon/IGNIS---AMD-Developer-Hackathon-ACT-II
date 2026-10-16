"""Exact-match micro precision, recall and F1 for entities and relations."""

from collections import Counter

from ignis_wo.extraction.adapters import ExtractionAdapter, gold_item_to_output
from ignis_wo.extraction.validate import validate_output
from ignis_wo.hosted.transport import ProviderError


def truncate_type(type_path: str, depth: int | None) -> str:
    if depth is None:
        return type_path
    parts = type_path.split("/")
    return "/".join(parts[:depth])


def entity_set(output: dict | None, depth: int | None) -> set:
    if not output:
        return set()
    return {(entity["start"], entity["end"], truncate_type(entity["type"], depth)) for entity in output["entities"]}


def relation_set(output: dict | None) -> set:
    if not output:
        return set()
    spans = {entity["id"]: (entity["start"], entity["end"]) for entity in output["entities"]}
    return {(spans[relation["head"]], spans[relation["tail"]], relation["type"]) for relation in output["relations"]}


def micro_scores(gold_sets: list[set], predicted_sets: list[set]) -> dict:
    gold_total = sum(len(gold) for gold in gold_sets)
    predicted_total = sum(len(predicted) for predicted in predicted_sets)
    correct = sum(len(gold & predicted) for gold, predicted in zip(gold_sets, predicted_sets))
    precision = correct / predicted_total if predicted_total else 0.0
    recall = correct / gold_total if gold_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "gold": gold_total,
        "predicted": predicted_total,
        "correct": correct,
    }


def perturb(output: dict, index: int) -> dict:
    """Deterministic errors used to prove the scorer notices mistakes."""
    entities = [dict(entity) for entity in output["entities"]]
    relations = list(output["relations"])
    if index % 3 == 0 and entities:
        entities[0]["type"] = "Activity" if entities[0]["type"] != "Activity" else "PhysicalObject"
    if index % 4 == 0 and relations:
        relations.pop()
    return {"entities": entities, "relations": relations}


def score_items(
    items: list[dict],
    adapter: ExtractionAdapter,
    depth: int | None = None,
    perturbed: bool = False,
) -> dict:
    gold_entities, predicted_entities = [], []
    gold_relations, predicted_relations = [], []
    invalid = 0
    provider_failures = Counter()
    for index, item in enumerate(items):
        text_norm, gold = gold_item_to_output(item)
        prediction, failed = None, False
        try:
            raw_prediction = adapter.extract(text_norm)
        except ProviderError as error:
            if not error.record_level:
                raise
            provider_failures[error.kind] += 1
            raw_prediction, failed = None, True
        if perturbed and raw_prediction:
            raw_prediction = perturb(raw_prediction, index)
        if not failed:
            prediction, errors = validate_output(raw_prediction, text_norm)
            invalid += bool(errors)
        predicted = prediction.model_dump() if prediction else None
        gold_entities.append(entity_set(gold, depth))
        predicted_entities.append(entity_set(predicted, depth))
        gold_relations.append(relation_set(gold))
        predicted_relations.append(relation_set(predicted))
    return {
        "items": len(items),
        "schema_invalid": invalid,
        "provider_failures": dict(sorted(provider_failures.items())),
        "entity_type_depth": depth,
        "entities": micro_scores(gold_entities, predicted_entities),
        "relations": micro_scores(gold_relations, predicted_relations),
    }
