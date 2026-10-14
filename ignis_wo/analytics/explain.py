"""Builds the typed per-component explanation from facts, and validates any explanation against them."""

from ignis_wo.analytics.triage import band_for, severity_for
from ignis_wo.contracts import ComponentExplanation, FactRow, Snapshot

MAX_EXAMPLES = 3


def facts_by_id(facts: list[FactRow]) -> dict[str, FactRow]:
    return {fact.fact_id: fact for fact in facts}


def facts_for_component(facts: list[FactRow], component: str) -> dict[str, FactRow]:
    by_kind = {}
    for fact in facts:
        if fact.scope.get("component") == component and fact.kind != "component_fault_count":
            by_kind[fact.kind] = fact
    return by_kind


def dominant_fault(facts: list[FactRow], component: str) -> FactRow | None:
    """Most records first, then higher severity, then class name, so ties resolve the same way every run."""
    candidates = [
        fact
        for fact in facts
        if fact.kind == "component_fault_count" and fact.scope["component"] == component
    ]
    if not candidates:
        return None

    def rank(fact: FactRow):
        fault_class = fact.scope["fault_class"]
        return (-fact.value, -severity_for(fault_class), fault_class)

    return min(candidates, key=rank)


def snapshot_caveats(snapshot: Snapshot, adapter_mode: str, synthetic: bool) -> list[str]:
    records = [entry.record for entry in snapshot.entries]
    caveats = []
    if any(fault.component is None for entry in snapshot.entries for fault in entry.projection.faults):
        caveats.append("UNATTRIBUTED_FAULTS")
    if any(record.asset_id is None for record in records):
        caveats.append("NO_ASSET_ID")
    if any(record.event_date is None for record in records):
        caveats.append("NO_DATES")
    if synthetic:
        caveats.append("SYNTHETIC_DATA")
    if adapter_mode == "fixture":
        caveats.append("FIXTURE_MODE")
    return caveats


def build_explanations(
    snapshot: Snapshot,
    facts: list[FactRow],
    adapter_mode: str,
    synthetic: bool,
) -> list[ComponentExplanation]:
    shared_caveats = snapshot_caveats(snapshot, adapter_mode, synthetic)
    components = sorted({fact.scope["component"] for fact in facts if fact.kind == "triage_score"})
    explanations = []
    for component in components:
        by_kind = facts_for_component(facts, component)
        triage = by_kind["triage_score"]
        recurrence = by_kind["recurrence"]
        criticality = by_kind["criticality"]
        dominant = dominant_fault(facts, component)
        caveats = list(shared_caveats)
        if criticality.reason and criticality.reason.startswith("default"):
            caveats.append("CRITICALITY_DEFAULT")
        if recurrence.value == 1:
            caveats.append("SINGLE_RECORD")
        explanations.append(
            ComponentExplanation(
                component=component,
                band=band_for(triage.value),
                triage_fact_id=triage.fact_id,
                severity_fact_id=by_kind["severity"].fact_id,
                recurrence_fact_id=recurrence.fact_id,
                criticality_fact_id=criticality.fact_id,
                dominant_fault_class=dominant.scope["fault_class"] if dominant else None,
                dominant_fault_fact_id=dominant.fact_id if dominant else None,
                example_record_ids=recurrence.record_ids[:MAX_EXAMPLES],
                caveats=caveats,
            )
        )
    known = facts_by_id(facts)

    def priority_order(explanation: ComponentExplanation):
        score = known[explanation.triage_fact_id].value
        return (-score, explanation.component)

    explanations.sort(key=priority_order)
    return explanations


def validate_explanation(explanation: ComponentExplanation, facts: list[FactRow]) -> list[str]:
    known = facts_by_id(facts)
    expected_kinds = {
        "triage_fact_id": "triage_score",
        "severity_fact_id": "severity",
        "recurrence_fact_id": "recurrence",
        "criticality_fact_id": "criticality",
        "dominant_fault_fact_id": "component_fault_count",
    }
    errors = []
    for field, kind in expected_kinds.items():
        referenced = getattr(explanation, field)
        if referenced is None:
            continue
        fact = known.get(referenced)
        if fact is None:
            errors.append(f"{field}: unknown fact {referenced}")
        elif fact.kind != kind or fact.scope.get("component") != explanation.component:
            errors.append(f"{field}: fact {referenced} is not the {kind} of {explanation.component}")
    if errors:
        return errors

    triage = known[explanation.triage_fact_id]
    if band_for(triage.value) != explanation.band:
        errors.append(f"band {explanation.band!r} does not match triage score {triage.value}")
    recurrence = known[explanation.recurrence_fact_id]
    if not set(explanation.example_record_ids) <= set(recurrence.record_ids):
        errors.append("example records are not among the component's approved records")
    dominant = dominant_fault(facts, explanation.component)
    expected_class = dominant.scope["fault_class"] if dominant else None
    if explanation.dominant_fault_class != expected_class:
        errors.append(f"dominant fault class should be {expected_class!r}")
    return errors
