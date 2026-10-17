"""Evidence-linked PDF: every number in the body is a checked claim or a fact row with its id."""

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab import rl_config
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ignis_wo.contracts import ComponentExplanation, FactRow, ReportClaim, Snapshot
from ignis_wo.render.templates import class_label, format_value, kpi_label

rl_config.invariant = 1

STYLES = getSampleStyleSheet()
TABLE_STYLE = TableStyle(
    [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
)


def heading(text: str) -> Paragraph:
    return Paragraph(escape(text), STYLES["Heading2"])


def paragraph(text: str) -> Paragraph:
    return Paragraph(escape(text), STYLES["BodyText"])


def table(rows: list[list[str]], widths: list[float]) -> Table:
    cells = [[paragraph(str(cell)) for cell in row] for row in rows]
    grid = Table(cells, colWidths=[width * mm for width in widths], repeatRows=1)
    grid.setStyle(TABLE_STYLE)
    return grid


def bar_chart(labels: list[str], values: list[float]) -> Drawing:
    height = max(46, 9 * len(labels) + 14) * mm / 2
    drawing = Drawing(170 * mm, height)
    chart = HorizontalBarChart()
    chart.x = 66 * mm
    chart.y = 12
    chart.width = 94 * mm
    chart.height = drawing.height - 24
    chart.data = [list(reversed(values))]
    chart.categoryAxis.categoryNames = list(reversed(labels))
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontSize = 7
    chart.bars[0].fillColor = colors.HexColor("#4a6fa5")
    drawing.add(chart)
    return drawing


def cover(snapshot: Snapshot, run_info: dict) -> list:
    banner = f"{run_info['data_label']} / {run_info['adapter_mode'].upper()} MODE"
    rows = [
        ["Field", "Value"],
        ["Snapshot", snapshot.snapshot_id],
        ["Adapter", f"{run_info['adapter_mode']}: {run_info['model_id']}@{run_info['model_version']}"],
        ["Extraction configuration", run_info.get("extraction_configuration", "not recorded")],
        ["Source file", f"{run_info['source_name']} (sha256 {run_info['source_sha256'][:16]})"],
        ["Mapping revision", run_info["mapping_revision"]],
        ["Reviewer", run_info["reviewer"]],
    ]
    for name, version in sorted(snapshot.config_versions.items()):
        rows.append([name, version])
    return [
        Paragraph("Maintenance work-order report", STYLES["Title"]),
        heading("1. Document control"),
        Paragraph(f'<font color="#b00020"><b>{escape(banner)}</b></font>', STYLES["Heading3"]),
        paragraph("Triage priority is a rule-based ordering from approved records. It is not a failure prediction."),
        table(rows, [45, 125]),
    ]


def fault_section(facts: list[FactRow]) -> list:
    class_facts = [fact for fact in facts if fact.kind == "fault_class_count"]
    class_facts.sort(key=lambda fact: (-fact.value, fact.scope["fault_class"]))
    labels = [class_label(fact.scope["fault_class"]) for fact in class_facts]
    values = [fact.value for fact in class_facts]
    rows = [["Fault class", "Records", "Fact"]]
    for label, fact in zip(labels, class_facts):
        rows.append([label, format_value(fact), fact.fact_id])
    content = [heading("4. Fault classes (Pareto)")]
    if class_facts:
        content.append(bar_chart(labels, values))
    content.append(table(rows, [80, 30, 60]))
    if class_facts:
        content.insert(-1, Spacer(1, 4 * mm))
    return content


def action_section(facts: list[FactRow]) -> list:
    action_facts = [fact for fact in facts if fact.kind == "action_count"]
    action_facts.sort(key=lambda fact: (-fact.value, fact.scope["action"]))
    rows = [["Action class", "Records", "Fact"]]
    for fact in action_facts:
        rows.append([class_label(fact.scope["action"]), format_value(fact), fact.fact_id])
    return [heading("5. Actions recorded"), table(rows, [80, 30, 60])]


def triage_section(explanations: list[ComponentExplanation], known: dict[str, FactRow], limit: int) -> list:
    rows = [["Component", "Band", "Priority", "Severity", "Recurrence", "Criticality", "Fact"]]
    for explanation in explanations[:limit]:
        triage = known[explanation.triage_fact_id]
        rows.append(
            [
                explanation.component,
                explanation.band,
                format_value(triage),
                format_value(known[explanation.severity_fact_id]),
                format_value(known[explanation.recurrence_fact_id]),
                format_value(known[explanation.criticality_fact_id]),
                triage.fact_id,
            ]
        )
    note = "Priority = severity x recurrence x criticality, computed in code from the approved snapshot."
    return [KeepTogether([heading("6. Triage priority"), paragraph(note), table(rows, [25, 31, 18, 17, 21, 20, 38])])]


def kpi_section(facts: list[FactRow]) -> list:
    rows = [["Indicator", "Value", "Status", "Fact"]]
    for fact in facts:
        if fact.kind != "kpi":
            continue
        value = format_value(fact) if fact.status == "computed" else "not computed"
        status = fact.status if fact.status == "computed" else fact.reason
        rows.append([kpi_label(fact.scope["kpi"]), value, status, fact.fact_id])
    return [heading("8. Reliability indicators"), table(rows, [45, 25, 70, 30])]


def example_section(explanations: list[ComponentExplanation], snapshot: Snapshot, limit: int) -> list:
    text_by_record = {entry.record.record_id: entry.record.text_norm for entry in snapshot.entries}
    rows = [["Component", "Record", "Work-order text"]]
    for explanation in explanations[:limit]:
        for record_id in explanation.example_record_ids:
            rows.append([explanation.component, record_id, text_by_record[record_id]])
    return [heading("9. Example events"), table(rows, [35, 35, 100])]


def build_pdf(
    path: Path,
    snapshot: Snapshot,
    facts: list[FactRow],
    explanations: list[ComponentExplanation],
    claims: list[ReportClaim],
    run_info: dict,
    top_components: int = 15,
    context_review: dict | None = None,
) -> None:
    known = {fact.fact_id: fact for fact in facts}
    claims_by_template = {}
    for claim in claims:
        claims_by_template.setdefault(claim.template_id, []).append(claim)
    top_names = {explanation.component for explanation in explanations[:top_components]}

    story = cover(snapshot, run_info)
    story.append(heading("2. Summary"))
    for claim in claims_by_template.get("summary.records", []):
        story.append(paragraph(claim.text))
    for claim in claims_by_template.get("component.triage", [])[:5]:
        story.append(paragraph(claim.text))

    story.append(heading("3. Data basis"))
    for line in run_info["data_basis"]:
        story.append(paragraph(line))

    story.extend(fault_section(facts))
    story.extend(action_section(facts))
    story.extend(triage_section(explanations, known, top_components))

    story.append(heading("7. Component explanations"))
    for claim in claims:
        if claim.subject_scope.get("component") in top_names:
            story.append(paragraph(claim.text))

    story.extend(kpi_section(facts))
    story.extend(example_section(explanations, snapshot, 5))
    story.append(heading("10. Engineer notes"))
    story.append(paragraph("Reserved for the reviewing engineer. No repair recommendation is generated."))
    story.append(Spacer(1, 30 * mm))

    rows = [["Claim", "Template", "Facts"]]
    for claim in claims:
        fact_ids = ", ".join(slot.fact_id for slot in claim.slots) or "none"
        rows.append([claim.claim_id, claim.template_id, fact_ids])
    story.append(KeepTogether([heading("11. Claim-to-fact appendix"), table(rows, [35, 45, 90])]))

    if context_review is not None:
        story.append(heading("12. Context review and provenance"))
        story.append(paragraph(f"Review status: {context_review.get('review_status', context_review.get('decision', 'unavailable'))}."))
        story.append(paragraph(f"Snapshot: {context_review.get('snapshot_id', snapshot.snapshot_id)}; evidence pack: {context_review.get('pack_id') or 'none'}."))
        story.append(paragraph(f"Explanation mode: {context_review.get('explanation_mode', 'unavailable')}; prompt identity: {context_review.get('prompt_id', 'none configured')}."))
        story.append(paragraph(f"Explanation model identity: {context_review.get('model_id', 'unavailable')}."))
        story.append(paragraph(f"Corpus: {context_review.get('corpus_mode') or 'not recorded'}; version {context_review.get('corpus_version') or 'none'}."))
        for source in context_review.get("sources", []):
            story.append(paragraph(f"Evidence source {source['passage_id']}: {source['document_id']} version {source['version']}, {source['location']}, "
                                   f"file sha256 {source['source_sha256'] or 'n/a'}, reader {source['reader']}."))
        story.append(paragraph("Contextual output is an expert-reviewed hypothesis and does not establish causation or authorize maintenance action."))
        draft = context_review.get("approved_draft")
        if draft:
            story.append(paragraph(f"Draft hash: {context_review.get('draft_hash', 'unavailable')}"))
            for label in ("hypotheses", "alternatives"):
                for claim in draft.get(label, []):
                    citations = ", ".join(claim.get("citations", []))
                    story.append(paragraph(f"{label.title()}: {claim.get('text', '')} [references: {citations}]"))
            story.append(paragraph(f"Uncertainty: {draft.get('uncertainty', 'not supplied')}"))
            if draft.get("inspection"):
                story.append(paragraph(f"Suggested inspection for expert consideration: {draft['inspection'].get('text', '')} [references: {', '.join(draft['inspection'].get('citations', []))}]"))
        else:
            story.append(paragraph(f"No contextual draft was included: {context_review.get('reason', 'context unavailable or not approved')}. Facts and numeric alerts remain independently computed."))
        story.append(paragraph(f"Expert reviewer: {context_review.get('reviewer', 'none')}; review time: {context_review.get('reviewed_at', 'none')}; review revision: {context_review.get('revision', 'none')}."))
        if context_review.get("reason"):
            story.append(paragraph(f"Review note: {context_review['reason']}"))

    document = SimpleDocTemplate(str(path), pagesize=A4, title="Maintenance work-order report", author="ignis_wo")
    document.build(story)
