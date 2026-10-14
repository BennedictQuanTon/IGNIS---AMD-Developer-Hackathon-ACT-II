"""Typed records passed between pipeline stages."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceFile(Contract):
    sha256: str
    name: str
    parser_id: str
    parser_version: str


class Locator(Contract):
    sheet: str | None = None
    row: int


class RawRow(Contract):
    locator: Locator
    values: dict[str, str]


class MappingProposal(Contract):
    method: str
    mapping: dict[str, str | None]
    evidence: dict[str, str]


class MappingRevision(Contract):
    revision_id: str
    proposal_hash: str
    mapping: dict[str, str | None]
    confirmed_by: str
    reason: str


class CanonicalRecord(Contract):
    record_id: str
    locator: Locator
    text: str
    text_norm: str
    normalizer_version: str
    work_order_id: str | None = None
    asset_id: str | None = None
    event_date: str | None = None
    downtime_hours: float | None = None
    source_priority: str | None = None


class Entity(Contract):
    id: str
    type: str
    start: int
    end: int
    text: str


class Relation(Contract):
    head: str
    tail: str
    type: str


class ExtractionOutput(Contract):
    entities: list[Entity]
    relations: list[Relation]


class ExtractionSuggestion(Contract):
    suggestion_id: str
    record_id: str
    adapter_mode: str
    model_id: str
    model_version: str
    task: str
    input_hash: str
    status: Literal["needs_review", "failed_terminal"]
    output: ExtractionOutput | None
    errors: list[str]
    confidence: float | None = None


class ReviewedAnnotation(Contract):
    annotation_id: str
    record_id: str
    suggestion_id: str
    status: Literal["accepted", "corrected", "rejected"]
    output: ExtractionOutput | None
    reviewer: str
    revision: int
    reason: str


class ComponentCriticality(Contract):
    component: str
    value: int = Field(ge=1)
    reason: str
    set_by: str


class FaultMention(Contract):
    component: str | None
    fault_class: str
    text: str


class RecordProjection(Contract):
    record_id: str
    components: list[str]
    faults: list[FaultMention]
    actions: list[str]


class SnapshotEntry(Contract):
    record: CanonicalRecord
    annotation_id: str
    projection: RecordProjection


class Snapshot(Contract):
    snapshot_id: str
    entries: list[SnapshotEntry]
    criticalities: list[ComponentCriticality]
    config_versions: dict[str, str]


FactKind = Literal[
    "record_count",
    "fault_class_count",
    "action_count",
    "component_fault_count",
    "severity",
    "recurrence",
    "criticality",
    "triage_score",
    "kpi",
]


class FactRow(Contract):
    fact_id: str
    snapshot_id: str
    kind: FactKind
    scope: dict[str, str]
    value: float | None
    unit: Literal["records", "severity_points", "multiplier", "score", "hours"]
    status: Literal["computed", "not_computed"]
    reason: str | None = None
    record_ids: list[str]
    input_fact_ids: list[str] = []
    config_version: str


Caveat = Literal[
    "UNATTRIBUTED_FAULTS",
    "NO_ASSET_ID",
    "NO_DATES",
    "CRITICALITY_DEFAULT",
    "SINGLE_RECORD",
    "SYNTHETIC_DATA",
    "FIXTURE_MODE",
]


class ComponentExplanation(Contract):
    component: str
    band: str
    triage_fact_id: str
    severity_fact_id: str
    recurrence_fact_id: str
    criticality_fact_id: str
    dominant_fault_class: str | None
    dominant_fault_fact_id: str | None
    example_record_ids: list[str]
    caveats: list[Caveat]


class ClaimSlot(Contract):
    role: str
    fact_id: str
    expected_kind: FactKind
    expected_unit: str


class ReportClaim(Contract):
    claim_id: str
    template_id: str
    template: str
    subject_scope: dict[str, str]
    slots: list[ClaimSlot]
    labels: dict[str, str]
    text: str
