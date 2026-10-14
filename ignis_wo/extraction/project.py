"""Projects MaintIE entities onto the component, fault and action view used for counting."""

from ignis_wo.analytics.triage import severity_for
from ignis_wo.contracts import ExtractionOutput, FaultMention, RecordProjection


def component_name(text: str) -> str:
    return " ".join(text.lower().split())


def project(record_id: str, output: ExtractionOutput) -> RecordProjection:
    entities = {entity.id: entity for entity in output.entities}
    component_ids = [entity.id for entity in output.entities if entity.type.startswith("PhysicalObject")]
    fault_ids = [entity.id for entity in output.entities if severity_for(entity.type) > 0]
    actions = [entity.type for entity in output.entities if entity.type.startswith("Activity")]

    linked: dict[str, list[str]] = {fault_id: [] for fault_id in fault_ids}
    for relation in output.relations:
        if relation.head in linked and relation.tail in component_ids:
            linked[relation.head].append(relation.tail)
        if relation.tail in linked and relation.head in component_ids:
            linked[relation.tail].append(relation.head)

    faults = []
    for fault_id in fault_ids:
        fault = entities[fault_id]
        targets = list(dict.fromkeys(linked[fault_id]))
        if not targets and len(component_ids) == 1:
            targets = component_ids
        if not targets:
            faults.append(FaultMention(component=None, fault_class=fault.type, text=fault.text))
        for target in targets:
            name = component_name(entities[target].text)
            faults.append(FaultMention(component=name, fault_class=fault.type, text=fault.text))

    components = sorted({component_name(entities[entity_id].text) for entity_id in component_ids})
    return RecordProjection(record_id=record_id, components=components, faults=faults, actions=sorted(actions))
