"""Sentence templates whose numbers can only come from fact slots."""

import re

from ignis_wo.contracts import ComponentExplanation, FactRow, ReportClaim, Snapshot
from ignis_wo.hashing import canonical_json, short_id

SLOT_PATTERN = re.compile(r"\{\{(fact|label):(\w+)\}\}")

# template id -> (template text, {fact role: (expected kind, expected unit)})
TEMPLATES = {
    "summary.records": (
        "The approved snapshot contains {{fact:records}} work-order records.",
        {"records": ("record_count", "records")},
    ),
    "fault_class.count": (
        "Approved records with {{label:fault_class}}: {{fact:count}}.",
        {"count": ("fault_class_count", "records")},
    ),
    "component.triage": (
        "{{label:component}} has triage priority {{fact:score}} ({{label:band}}): severity {{fact:severity}}"
        " × recurrence {{fact:recurrence}} × criticality {{fact:criticality}}.",
        {
            "score": ("triage_score", "score"),
            "severity": ("severity", "severity_points"),
            "recurrence": ("recurrence", "records"),
            "criticality": ("criticality", "multiplier"),
        },
    ),
    "component.dominant_fault": (
        "The most frequent reviewed fault class for {{label:component}} is {{label:fault_class}}"
        " (records: {{fact:count}}).",
        {"count": ("component_fault_count", "records")},
    ),
    "component.criticality_default": (
        "Criticality for {{label:component}} is the default because no supervisor rating was set.",
        {},
    ),
    "kpi.downtime": (
        "Total recorded downtime is {{fact:hours}} hours.",
        {"hours": ("kpi", "hours")},
    ),
    "kpi.not_computed": (
        "{{label:kpi}} was not computed: {{label:reason}}.",
        {},
    ),
}


def class_label(class_path: str) -> str:
    leaf = class_path.split("/")[-1]
    words = re.findall(r"[A-Z][a-z]*", leaf)
    return " ".join(words).lower() or leaf


def kpi_label(kpi: str) -> str:
    return kpi.replace("_", " ").capitalize()


def format_value(fact: FactRow) -> str:
    if fact.value is None:
        raise ValueError(f"fact {fact.fact_id} has no value")
    if fact.unit == "hours":
        return f"{fact.value:.1f}"
    return str(int(fact.value))


def render(template: str, fact_values: dict[str, str], labels: dict[str, str]) -> str:
    def fill(match: re.Match) -> str:
        slot_type, role = match.groups()
        return fact_values[role] if slot_type == "fact" else labels[role]

    return SLOT_PATTERN.sub(fill, template)


def make_claim(
    template_id: str,
    subject_scope: dict[str, str],
    facts: dict[str, FactRow],
    labels: dict[str, str] | None = None,
) -> ReportClaim:
    template, roles = TEMPLATES[template_id]
    labels = labels or {}
    slots = []
    for role, (kind, unit) in roles.items():
        slots.append({"role": role, "fact_id": facts[role].fact_id, "expected_kind": kind, "expected_unit": unit})
    fact_values = {role: format_value(fact) for role, fact in facts.items()}
    fact_ids = [slot["fact_id"] for slot in slots]
    claim_id = short_id("C", template_id, canonical_json(subject_scope), canonical_json(labels), *fact_ids)
    return ReportClaim(
        claim_id=claim_id,
        template_id=template_id,
        template=template,
        subject_scope=subject_scope,
        slots=slots,
        labels=labels,
        text=render(template, fact_values, labels),
    )


def explanation_claims(explanation: ComponentExplanation, known: dict[str, FactRow]) -> list[ReportClaim]:
    component = explanation.component
    scope = {"component": component}
    triage_facts = {
        "score": known[explanation.triage_fact_id],
        "severity": known[explanation.severity_fact_id],
        "recurrence": known[explanation.recurrence_fact_id],
        "criticality": known[explanation.criticality_fact_id],
    }
    claims = [make_claim("component.triage", scope, triage_facts, {"component": component, "band": explanation.band})]
    if explanation.dominant_fault_fact_id:
        dominant = known[explanation.dominant_fault_fact_id]
        labels = {"component": component, "fault_class": class_label(explanation.dominant_fault_class)}
        claims.append(make_claim("component.dominant_fault", scope, {"count": dominant}, labels))
    if "CRITICALITY_DEFAULT" in explanation.caveats:
        claims.append(make_claim("component.criticality_default", scope, {}, {"component": component}))
    return claims


def build_claims(
    snapshot: Snapshot,
    facts: list[FactRow],
    explanations: list[ComponentExplanation],
) -> list[ReportClaim]:
    known = {fact.fact_id: fact for fact in facts}
    record_count = next(fact for fact in facts if fact.kind == "record_count")
    claims = [make_claim("summary.records", {}, {"records": record_count})]

    for fact in facts:
        if fact.kind == "fault_class_count":
            labels = {"fault_class": class_label(fact.scope["fault_class"])}
            claims.append(make_claim("fault_class.count", fact.scope, {"count": fact}, labels))

    for explanation in explanations:
        claims.extend(explanation_claims(explanation, known))

    for fact in facts:
        if fact.kind != "kpi":
            continue
        if fact.status == "computed":
            claims.append(make_claim("kpi.downtime", fact.scope, {"hours": fact}))
        else:
            labels = {"kpi": kpi_label(fact.scope["kpi"]), "reason": fact.reason}
            claims.append(make_claim("kpi.not_computed", fact.scope, {}, labels))
    return claims
