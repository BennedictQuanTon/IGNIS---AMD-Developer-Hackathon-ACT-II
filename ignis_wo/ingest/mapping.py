"""Proposes a column mapping, records who confirmed it, and builds canonical records."""

import datetime
import math
import re

from ignis_wo.contracts import CanonicalRecord, MappingProposal, MappingRevision, RawRow, SourceFile
from ignis_wo.hashing import content_hash, short_id

NORMALIZER_VERSION = "normalize-v1"
MAPPING_METHOD = "header-synonyms-v1"

FIELD_SYNONYMS = {
    "text": ["description", "text", "work order description", "problem", "comment", "short text"],
    "work_order_id": ["work order", "wo", "wo number", "order id", "work order id", "wo id"],
    "asset_id": ["asset", "asset id", "equipment", "equipment id", "functional location"],
    "event_date": ["date", "reported date", "event date", "created", "reported on"],
    "downtime_hours": ["downtime", "downtime hours", "downtime h", "hours down"],
    "source_priority": ["priority", "source priority"],
}


def normalize_header(header: str) -> str:
    lowered = header.lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def normalize_text(text: str) -> str:
    """Collapses whitespace only; case is kept so spans match the source text."""
    return " ".join(text.split())


def propose_mapping(columns: list[str]) -> MappingProposal:
    mapping: dict[str, str | None] = {}
    evidence: dict[str, str] = {}
    for field, synonyms in FIELD_SYNONYMS.items():
        mapping[field] = None
        for column in columns:
            header = normalize_header(column)
            if header in synonyms:
                mapping[field] = column
                evidence[field] = f"header {column!r} matches synonym {header!r}"
                break
    return MappingProposal(method=MAPPING_METHOD, mapping=mapping, evidence=evidence)


def confirm_mapping(
    proposal: MappingProposal,
    confirmed_by: str,
    reason: str,
    overrides: dict[str, str | None] | None = None,
) -> MappingRevision:
    mapping = dict(proposal.mapping)
    mapping.update(overrides or {})
    if not mapping.get("text"):
        raise ValueError("the mapping has no text column; a work-order description is required")
    proposal_hash = content_hash(proposal)
    revision_id = short_id("map", proposal_hash, content_hash(mapping), confirmed_by)
    return MappingRevision(
        revision_id=revision_id,
        proposal_hash=proposal_hash,
        mapping=mapping,
        confirmed_by=confirmed_by,
        reason=reason,
    )


def parse_hours(value: str) -> float | None:
    try:
        hours = float(value)
        return hours if math.isfinite(hours) and hours >= 0 else None
    except (TypeError, ValueError):
        return None


def parse_date(value: str) -> str | None:
    try:
        return datetime.date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        return None


def build_records(
    source_file: SourceFile,
    rows: list[RawRow],
    revision: MappingRevision,
) -> tuple[list[CanonicalRecord], list[str]]:
    records = []
    issues = []
    for row in rows:
        fields = {}
        for field, column in revision.mapping.items():
            value = row.values.get(column, "") if column else ""
            fields[field] = value or None
        where = f"row {row.locator.row}"
        if not fields["text"]:
            issues.append(f"{where}: rejected, empty text")
            continue
        downtime = None
        if fields["downtime_hours"]:
            unit_header = normalize_header(revision.mapping.get("downtime_hours") or "")
            if re.search(r"\b(minutes?|mins?|seconds?|secs?|days?)\b", unit_header):
                issues.append(f"{where}: downtime source unit is not hours; value left uncomputed")
                fields["downtime_hours"] = None
            else:
                raw_hours = fields["downtime_hours"]
                try:
                    parsed_hours = float(raw_hours)
                except (TypeError, ValueError):
                    issues.append(f"{where}: downtime is not a number, left empty")
                else:
                    if not math.isfinite(parsed_hours) or parsed_hours < 0:
                        issues.append(f"{where}: downtime is invalid (must be finite and nonnegative), left empty")
                    else:
                        downtime = parsed_hours
        else:
            issues.append(f"{where}: downtime hours missing; KPI may be not computed")
        event_date = None
        if fields["event_date"]:
            event_date = parse_date(fields["event_date"])
            if event_date is None:
                issues.append(f"{where}: date is not ISO formatted, left empty")
        else:
            issues.append(f"{where}: event date missing")
        record_id = short_id(
            "rec",
            source_file.sha256,
            str(row.locator.sheet),
            str(row.locator.row),
            source_file.parser_version,
            revision.revision_id,
        )
        record = CanonicalRecord(
            record_id=record_id,
            locator=row.locator,
            text=fields["text"],
            text_norm=normalize_text(fields["text"]),
            normalizer_version=NORMALIZER_VERSION,
            work_order_id=fields["work_order_id"],
            asset_id=fields["asset_id"],
            event_date=event_date,
            downtime_hours=downtime,
            source_priority=fields["source_priority"],
        )
        records.append(record)
    return records, issues
