"""Runs the adapter over each record and keeps every output, valid or not, with its reasons."""

from ignis_wo.contracts import CanonicalRecord, ExtractionSuggestion
from ignis_wo.extraction.adapters import TASK, ExtractionAdapter, input_hash
from ignis_wo.extraction.validate import validate_output
from ignis_wo.hashing import short_id


def suggest(record: CanonicalRecord, adapter: ExtractionAdapter) -> ExtractionSuggestion:
    raw_output = adapter.extract(record.text_norm)
    if raw_output is None:
        output, errors, status = None, ["no model output for this record"], "needs_review"
    else:
        output, errors = validate_output(raw_output, record.text_norm)
        status = "needs_review" if output else "failed_terminal"
    key = input_hash(record.text_norm)
    return ExtractionSuggestion(
        suggestion_id=short_id("sug", record.record_id, adapter.model_id, adapter.model_version, key),
        record_id=record.record_id,
        adapter_mode=adapter.mode,
        model_id=adapter.model_id,
        model_version=adapter.model_version,
        task=TASK,
        input_hash=key,
        status=status,
        output=output,
        errors=errors,
    )


def suggest_all(records: list[CanonicalRecord], adapter: ExtractionAdapter) -> list[ExtractionSuggestion]:
    return [suggest(record, adapter) for record in records]
