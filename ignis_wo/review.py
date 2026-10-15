"""Supervisor decisions on extraction suggestions; corrections are validated like model output."""

from ignis_wo.contracts import CanonicalRecord, ExtractionSuggestion, ReviewedAnnotation
from ignis_wo.extraction.validate import validate_output
from ignis_wo.hashing import content_hash, short_id
import datetime


def annotate(
    suggestion: ExtractionSuggestion,
    status: str,
    output,
    reviewer: str,
    reason: str,
    revision: int = 1,
    decided_at: str | None = None,
) -> ReviewedAnnotation:
    annotation_id = short_id("ann", suggestion.suggestion_id, status, content_hash(output), str(revision), reviewer)
    return ReviewedAnnotation(
        annotation_id=annotation_id,
        record_id=suggestion.record_id,
        suggestion_id=suggestion.suggestion_id,
        status=status,
        output=output,
        reviewer=reviewer,
        revision=revision,
        reason=reason,
        decided_at=decided_at or datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )


def accept_all(suggestions: list[ExtractionSuggestion], reviewer: str, reason: str) -> list[ReviewedAnnotation]:
    annotations = []
    for suggestion in suggestions:
        if suggestion.status == "needs_review" and suggestion.output is not None:
            annotations.append(annotate(suggestion, "accepted", suggestion.output, reviewer, reason))
    return annotations


def apply_decisions(
    suggestions: list[ExtractionSuggestion],
    records: list[CanonicalRecord],
    decisions: dict[str, dict],
    reviewer: str,
) -> list[ReviewedAnnotation]:
    """Decisions are keyed by record id: {"status", "reason", "output" (required when corrected)}."""
    text_by_record = {record.record_id: record.text_norm for record in records}
    annotations = []
    for suggestion in suggestions:
        decision = decisions.get(suggestion.record_id)
        if decision is None:
            continue
        status = decision["status"]
        reason = decision.get("reason", "")
        decision_reviewer = decision.get("reviewer", reviewer)
        if not isinstance(decision_reviewer, str) or not decision_reviewer.strip():
            raise ValueError(f"{suggestion.record_id}: reviewer attribution is required")
        if status == "accepted":
            if suggestion.output is None:
                raise ValueError(f"{suggestion.record_id}: cannot accept a suggestion without valid output")
            output = suggestion.output
        elif status == "corrected":
            output, errors = validate_output(decision.get("output"), text_by_record[suggestion.record_id])
            if errors:
                raise ValueError(f"{suggestion.record_id}: correction is invalid: {'; '.join(errors)}")
        elif status == "rejected":
            output = None
        else:
            raise ValueError(f"{suggestion.record_id}: unknown review status {status!r}")
        annotations.append(annotate(suggestion, status, output, decision_reviewer, reason, decision.get("revision", 1), decision.get("reviewed_at")))
    return annotations
