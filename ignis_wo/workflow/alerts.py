"""Versioned transition rules for historical work-order priority alerts."""
import json
from pathlib import Path
from ignis_wo.analytics.triage import band_for

RULES = json.loads((Path(__file__).resolve().parents[1] / "config" / "alert_rules_v1.json").read_text(encoding="utf-8"))
RULE_VERSION = RULES["version"]
CRITICALITY_POLICY_VERSION = RULES["criticality_policy_version"]
CRITICAL_THRESHOLD = RULES["criticality_value_minimum"]


def build_alerts(snapshot, facts, prior_snapshot=None, prior_facts=None):
    by_component = {f["scope"]["component"]: f for f in (fact.model_dump(mode="json") for fact in facts) if f["kind"] == "triage_score"}
    prior = {f["scope"]["component"]: f for f in (fact.model_dump(mode="json") for fact in (prior_facts or [])) if f["kind"] == "triage_score"}
    current_entries = {e.record.work_order_id or e.record.record_id: e for e in snapshot.entries}
    previous_entries = {e.record.work_order_id or e.record.record_id: e for e in (prior_snapshot.entries if prior_snapshot else [])}
    alerts = []
    for component, triage in sorted(by_component.items()):
        band = band_for(triage["value"])
        old = prior.get(component)
        if band == "High" and old is None:
            alerts.append({"alert_id": f"{snapshot.snapshot_id}:{component}:initial", "type": "initial_high_notice", "component": component, "snapshot_id": snapshot.snapshot_id, "rule_version": RULE_VERSION, "status": "active", "message": "Initial High band; this is not a crossing claim."})
        elif band == "High" and band_for(old["value"]) != "High":
            alerts.append({"alert_id": f"{snapshot.snapshot_id}:{component}:crossing", "type": "high_band_crossing", "component": component, "snapshot_id": snapshot.snapshot_id, "rule_version": RULE_VERSION, "status": "active", "linked_snapshot_id": prior_snapshot.snapshot_id, "message": "Approved snapshot moved from below High into High."})
        criticality = next((rating.value for rating in snapshot.criticalities if rating.component == component), 1)
        if criticality >= CRITICAL_THRESHOLD:
            current_failed = {rid for rid, e in current_entries.items() if component in e.projection.components and any(f.component == component and f.fault_class.endswith("/FailedState") for f in e.projection.faults)}
            old_failed = {rid for rid, e in previous_entries.items() if component in e.projection.components and any(f.component == component and f.fault_class.endswith("/FailedState") for f in e.projection.faults)}
            for record_id in sorted(current_failed - old_failed):
                alerts.append({"alert_id": f"{snapshot.snapshot_id}:{component}:failed:{record_id}", "type": "critical_component_failed_state", "component": component, "record_id": record_id, "snapshot_id": snapshot.snapshot_id, "rule_version": RULE_VERSION, "criticality_policy_version": CRITICALITY_POLICY_VERSION, "status": "active", "message": f"New FailedState on supervisor-rated critical component (criticality >= {CRITICAL_THRESHOLD})."})
    if prior_snapshot:
        prior_failed = {rid: e for rid, e in previous_entries.items() if any(f.fault_class.endswith("/FailedState") for f in e.projection.faults)}
        for record_id, entry in sorted(prior_failed.items()):
            new_entry = current_entries.get(record_id)
            removed = new_entry is None or not any(f.fault_class.endswith("/FailedState") for f in new_entry.projection.faults)
            for component in sorted(entry.projection.components):
                criticality = max((r.value for r in snapshot.criticalities if r.component == component), default=1)
                if removed and criticality >= CRITICAL_THRESHOLD:
                    alerts.append({"alert_id": f"{snapshot.snapshot_id}:{component}:retraction:{record_id}", "type": "finding_retracted", "component": component, "record_id": record_id, "snapshot_id": snapshot.snapshot_id, "linked_snapshot_id": prior_snapshot.snapshot_id, "rule_version": RULE_VERSION, "status": "retracted", "message": "A previously included FailedState record is absent from the corrected snapshot."})
    return alerts
