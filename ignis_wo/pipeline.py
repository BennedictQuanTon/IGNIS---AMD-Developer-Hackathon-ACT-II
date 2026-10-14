"""Runs every stage in order, persisting each stage's artifact before the next one starts."""

from dataclasses import dataclass, field
from pathlib import Path

from ignis_wo.analytics.explain import build_explanations, validate_explanation
from ignis_wo.analytics.facts import FACTS_VERSION, compute_facts
from ignis_wo.artifacts import StageWriter
from ignis_wo.config import load_config
from ignis_wo.contracts import ComponentCriticality
from ignis_wo.extraction.adapters import ExtractionAdapter, ReplayMiss
from ignis_wo.extraction.suggest import suggest_all
from ignis_wo.hashing import sha256_bytes
from ignis_wo.ingest.mapping import NORMALIZER_VERSION, build_records, confirm_mapping, propose_mapping
from ignis_wo.ingest.registry import PARSER_VERSION, parse_file
from ignis_wo.render.board import build_board
from ignis_wo.render.claims import check_claims
from ignis_wo.render.pdf import build_pdf
from ignis_wo.render.templates import build_claims
from ignis_wo.review import accept_all, apply_decisions
from ignis_wo.snapshot import build_snapshot


@dataclass
class RunOptions:
    input_path: Path
    output_directory: Path
    adapter: ExtractionAdapter
    reviewer: str = "demo-script"
    synthetic: bool = False
    allow_rejected: bool = False
    mapping_overrides: dict | None = None
    decisions: dict | None = None
    criticalities: list[ComponentCriticality] = field(default_factory=list)


def config_versions(adapter: ExtractionAdapter) -> dict[str, str]:
    return {
        "severity": load_config("severity_v1")["version"],
        "triage": load_config("triage_v1")["version"],
        "labels": load_config("maintie_labels_v1")["version"],
        "facts": FACTS_VERSION,
        "normalizer": NORMALIZER_VERSION,
        "parser": PARSER_VERSION,
        "extraction_model": f"{adapter.model_id}@{adapter.model_version}",
    }


def run_pipeline(options: RunOptions) -> dict:
    writer = StageWriter(options.output_directory)
    adapter = options.adapter

    source_file, rows = parse_file(options.input_path)
    columns = sorted({column for row in rows for column in row.values})
    ingest = {"source_file": source_file, "columns": columns, "row_count": len(rows)}
    ingest_hash = writer.write("01_ingest", ingest, [source_file.sha256])

    proposal = propose_mapping(columns)
    reason = "heuristic mapping confirmed by the run operator"
    revision = confirm_mapping(proposal, options.reviewer, reason, options.mapping_overrides)
    records, issues = build_records(source_file, rows, revision)
    mapping = {"proposal": proposal, "revision": revision, "records": records, "issues": issues}
    if not records:
        writer.fail("02_mapping", ["no usable records"] + issues, mapping)
    mapping_hash = writer.write("02_mapping", mapping, [ingest_hash])

    try:
        suggestions = suggest_all(records, adapter)
    except ReplayMiss as error:
        writer.fail("03_extract", [str(error)])
    failed = [suggestion for suggestion in suggestions if suggestion.status == "failed_terminal"]
    if failed and not options.allow_rejected:
        errors = [f"{suggestion.record_id}: {'; '.join(suggestion.errors)}" for suggestion in failed]
        writer.fail("03_extract", errors, suggestions)
    extract_hash = writer.write("03_extract", suggestions, [mapping_hash])

    if options.decisions is None:
        annotations = accept_all(suggestions, options.reviewer, "accepted by the run operator")
    else:
        annotations = apply_decisions(suggestions, records, options.decisions, options.reviewer)
    review_hash = writer.write("04_review", annotations, [extract_hash])

    snapshot = build_snapshot(records, annotations, options.criticalities, config_versions(adapter))
    if not snapshot.entries:
        writer.fail("05_snapshot", ["no approved records"])
    snapshot_hash = writer.write("05_snapshot", snapshot, [review_hash])

    facts = compute_facts(snapshot)
    facts_hash = writer.write("06_facts", facts, [snapshot_hash])

    explanations = build_explanations(snapshot, facts, adapter.mode, options.synthetic)
    explanation_errors = []
    for explanation in explanations:
        for error in validate_explanation(explanation, facts):
            explanation_errors.append(f"{explanation.component}: {error}")
    if explanation_errors:
        writer.fail("07_explain", explanation_errors, explanations)
    explain_hash = writer.write("07_explain", explanations, [facts_hash])

    claims = build_claims(snapshot, facts, explanations)
    failures = check_claims(claims, facts, snapshot.snapshot_id)
    if failures:
        errors = [f"{claim_id}: {'; '.join(messages)}" for claim_id, messages in failures.items()]
        writer.fail("08_claims", errors, claims)
    claims_hash = writer.write("08_claims", claims, [facts_hash, explain_hash])

    data_label = "SYNTHETIC DATA" if options.synthetic else "SOURCE DATA"
    unreviewed = len(suggestions) - len(annotations)
    run_info = {
        "data_label": data_label,
        "adapter_mode": adapter.mode,
        "model_id": adapter.model_id,
        "model_version": adapter.model_version,
        "source_name": source_file.name,
        "source_sha256": source_file.sha256,
        "mapping_revision": revision.revision_id,
        "reviewer": options.reviewer,
        "data_basis": [
            f"Pipeline statistics: {len(rows)} rows read, {len(records)} records built, {len(issues)} ingest issues.",
            f"{len(failed)} extractions failed validation; {unreviewed} suggestions were not approved.",
            f"Snapshot {snapshot.snapshot_id} freezes {len(snapshot.entries)} approved records.",
        ],
    }
    pdf_path = options.output_directory / "report.pdf"
    build_pdf(pdf_path, snapshot, facts, explanations, claims, run_info)
    board_path = options.output_directory / "board.html"
    banner = f"{data_label} / {adapter.mode.upper()} MODE"
    build_board(board_path, snapshot.snapshot_id, explanations, facts, claims, banner)
    pdf_sha256 = sha256_bytes(pdf_path.read_bytes())
    report = {"pdf": pdf_path.name, "pdf_sha256": pdf_sha256, "board": board_path.name}
    writer.write("09_report", report, [claims_hash])
    return {"snapshot_id": snapshot.snapshot_id, "records": len(snapshot.entries), "pdf_sha256": pdf_sha256}
