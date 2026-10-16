"""Runs the adapter over each record and keeps every output, valid or not, with its reasons.

A bad answer for one record (invalid, empty or truncated) fails only that record. Rate limits,
outages, timeouts, auth and credit errors raise, so the stage fails without saving and can be retried.
"""

from ignis_wo.contracts import CanonicalRecord, ExtractionSuggestion
from ignis_wo.extraction.adapters import TASK, ExtractionAdapter, input_hash
from ignis_wo.extraction.validate import validate_output
from ignis_wo.hashing import short_id
from ignis_wo.hosted.transport import ProviderError


def suggest(record: CanonicalRecord, adapter: ExtractionAdapter) -> ExtractionSuggestion:
    output, errors, status = None, [], "needs_review"
    try:
        raw_output = adapter.extract(record.text_norm)
    except ProviderError as error:
        if not error.record_level:
            raise
        raw_output, errors, status = None, [f"provider_error: {error}"], "failed_terminal"
    if raw_output is not None:
        output, errors = validate_output(raw_output, record.text_norm)
        status = "needs_review" if output else "failed_terminal"
    elif not errors:
        errors = ["no model output for this record"]
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
