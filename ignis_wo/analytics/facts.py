"""Deterministic facts from an approved snapshot; every number carries its fact id and records."""

from collections import defaultdict

from ignis_wo.analytics.triage import severity_for
from ignis_wo.config import load_config
from ignis_wo.contracts import FactRow, Snapshot
from ignis_wo.hashing import canonical_json, sha256_text

FACTS_VERSION = "facts-v1"


def fact_id(kind: str, scope: dict[str, str], snapshot_id: str) -> str:
    digest = sha256_text(f"{kind}|{canonical_json(scope)}|{snapshot_id}")
    return "F-" + digest[:10]


class FactBuilder:
    def __init__(self, snapshot: Snapshot):
        self.snapshot_id = snapshot.snapshot_id
        self.facts: list[FactRow] = []

    def add(self, kind, scope, value, unit, record_ids, config_version=FACTS_VERSION, **extra) -> FactRow:
        fact = FactRow(
            fact_id=fact_id(kind, scope, self.snapshot_id),
            snapshot_id=self.snapshot_id,
            kind=kind,
            scope=scope,
            value=value,
            unit=unit,
            status=extra.pop("status", "computed"),
            record_ids=sorted(record_ids),
            config_version=config_version,
            **extra,
        )
        self.facts.append(fact)
        return fact


def group_records(snapshot: Snapshot):
    class_records = defaultdict(set)
    action_records = defaultdict(set)
    component_records = defaultdict(set)
    component_class_records = defaultdict(lambda: defaultdict(set))
    for entry in snapshot.entries:
        record_id = entry.record.record_id
        for component in entry.projection.components:
            component_records[component].add(record_id)
        for action in entry.projection.actions:
            action_records[action].add(record_id)
        for fault in entry.projection.faults:
            class_records[fault.fault_class].add(record_id)
            if fault.component:
                component_class_records[fault.component][fault.fault_class].add(record_id)
    return class_records, action_records, component_records, component_class_records


def add_component_facts(builder: FactBuilder, snapshot: Snapshot, component: str, records: set, classes: dict) -> None:
    severity_config = load_config("severity_v1")
    triage_config = load_config("triage_v1")
    ratings = {rating.component: rating for rating in snapshot.criticalities}
    scope = {"component": component}

    for fault_class, class_records in sorted(classes.items()):
        class_scope = {"component": component, "fault_class": fault_class}
        builder.add("component_fault_count", class_scope, len(class_records), "records", class_records)

    worst = max((severity_for(fault_class, severity_config) for fault_class in classes), default=0)
    worst_records = set()
    for fault_class, class_records in classes.items():
        if severity_for(fault_class, severity_config) == worst:
            worst_records |= class_records
    severity = builder.add("severity", scope, worst, "severity_points", worst_records, severity_config["version"])
    recurrence = builder.add("recurrence", scope, len(records), "records", records)

    rating = ratings.get(component)
    criticality_value = rating.value if rating else 1
    criticality_reason = rating.reason if rating else "default, no supervisor rating"
    criticality = builder.add("criticality", scope, criticality_value, "multiplier", [], reason=criticality_reason)

    score = worst * len(records) * criticality_value
    inputs = [severity.fact_id, recurrence.fact_id, criticality.fact_id]
    builder.add("triage_score", scope, score, "score", records, triage_config["version"], input_fact_ids=inputs)


def add_kpi_facts(builder: FactBuilder, snapshot: Snapshot) -> None:
    record_ids = [entry.record.record_id for entry in snapshot.entries]
    downtimes = [entry.record.downtime_hours for entry in snapshot.entries]
    if downtimes and None not in downtimes:
        total = round(sum(downtimes), 1)
        builder.add("kpi", {"kpi": "total_downtime"}, total, "hours", record_ids)
    else:
        reason = "downtime is missing on some or all records"
        builder.add("kpi", {"kpi": "total_downtime"}, None, "hours", [], status="not_computed", reason=reason)
    missing = {
        "mean_time_between_failures": "needs operating hours per asset, which the export does not contain",
        "mean_time_to_repair": "needs repair start and finish times, which the export does not contain",
    }
    for kpi, reason in missing.items():
        builder.add("kpi", {"kpi": kpi}, None, "hours", [], status="not_computed", reason=reason)


def compute_facts(snapshot: Snapshot) -> list[FactRow]:
    builder = FactBuilder(snapshot)
    all_records = [entry.record.record_id for entry in snapshot.entries]
    builder.add("record_count", {}, len(all_records), "records", all_records)

    class_records, action_records, component_records, component_class_records = group_records(snapshot)
    for fault_class, records in sorted(class_records.items()):
        builder.add("fault_class_count", {"fault_class": fault_class}, len(records), "records", records)
    for action, records in sorted(action_records.items()):
        builder.add("action_count", {"action": action}, len(records), "records", records)
    for component, records in sorted(component_records.items()):
        classes = component_class_records.get(component, {})
        add_component_facts(builder, snapshot, component, records, classes)

    add_kpi_facts(builder, snapshot)
    return builder.facts
