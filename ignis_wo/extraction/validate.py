"""Treats model output as untrusted: schema, labels, offsets and span text must all hold."""

from pydantic import ValidationError

from ignis_wo.config import entity_labels, relation_labels
from ignis_wo.contracts import ExtractionOutput


def validate_output(raw_output, text_norm: str) -> tuple[ExtractionOutput | None, list[str]]:
    try:
        output = ExtractionOutput.model_validate(raw_output)
    except ValidationError as error:
        return None, [f"schema: {issue['msg']} at {issue['loc']}" for issue in error.errors()]

    errors = []
    known_entities = entity_labels()
    known_relations = relation_labels()
    entity_ids = set()
    for entity in output.entities:
        if entity.id in entity_ids:
            errors.append(f"entity {entity.id}: duplicate id")
        entity_ids.add(entity.id)
        if entity.type not in known_entities:
            errors.append(f"entity {entity.id}: unknown label {entity.type!r}")
        if not 0 <= entity.start < entity.end <= len(text_norm):
            errors.append(f"entity {entity.id}: offsets {entity.start}-{entity.end} out of bounds")
        elif text_norm[entity.start:entity.end] != entity.text:
            errors.append(f"entity {entity.id}: span text does not match the source")

    for relation in output.relations:
        if relation.type not in known_relations:
            errors.append(f"relation {relation.head}->{relation.tail}: unknown type {relation.type!r}")
        if relation.head not in entity_ids or relation.tail not in entity_ids:
            errors.append(f"relation {relation.head}->{relation.tail}: refers to a missing entity")

    if errors:
        return None, errors
    return output, []
