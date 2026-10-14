"""Freezes approved records, criticality ratings and config versions under one content hash."""

from ignis_wo.contracts import CanonicalRecord, ComponentCriticality, ReviewedAnnotation, Snapshot, SnapshotEntry
from ignis_wo.extraction.project import project
from ignis_wo.hashing import content_hash


def build_snapshot(
    records: list[CanonicalRecord],
    annotations: list[ReviewedAnnotation],
    criticalities: list[ComponentCriticality],
    config_versions: dict[str, str],
) -> Snapshot:
    records_by_id = {record.record_id: record for record in records}
    approved = [annotation for annotation in annotations if annotation.status != "rejected"]
    approved.sort(key=lambda annotation: annotation.record_id)

    entries = []
    for annotation in approved:
        projection = project(annotation.record_id, annotation.output)
        record = records_by_id[annotation.record_id]
        entries.append(SnapshotEntry(record=record, annotation_id=annotation.annotation_id, projection=projection))

    sorted_criticalities = sorted(criticalities, key=lambda rating: rating.component)
    identity = {
        "annotations": [[entry.record.record_id, entry.annotation_id] for entry in entries],
        "criticalities": sorted_criticalities,
        "config_versions": config_versions,
    }
    snapshot_id = "S-" + content_hash(identity)[:16]
    return Snapshot(
        snapshot_id=snapshot_id,
        entries=entries,
        criticalities=sorted_criticalities,
        config_versions=config_versions,
    )
