"""Static, read-only triage board as a single HTML file."""

from html import escape
from pathlib import Path

from ignis_wo.contracts import ComponentExplanation, FactRow, ReportClaim
from ignis_wo.render.templates import format_value

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Triage board</title>
<style>
body {{ font: 14px system-ui, sans-serif; margin: 16px; color: #1d1d1f; background: #fafafa; }}
table {{ border-collapse: collapse; width: 100%; background: #fff; }}
th, td {{ border-bottom: 1px solid #ddd; padding: 6px 8px; text-align: left; vertical-align: top; }}
.High {{ color: #b00020; font-weight: 600; }} .Medium {{ color: #a15c00; font-weight: 600; }}
.banner {{ color: #b00020; font-weight: 600; }} code {{ font-size: 12px; color: #555; }}
</style></head><body>
<h1>Triage board</h1>
<p class="banner">{banner}</p>
<p>Snapshot <code>{snapshot_id}</code>. Triage priority is a rule-based ordering, not a failure prediction.</p>
<table><thead><tr><th>Component</th><th>Band</th><th>Priority</th><th>Explanation</th><th>Example records</th></tr></thead>
<tbody>
{rows}
</tbody></table></body></html>
"""


def build_board(
    path: Path,
    snapshot_id: str,
    explanations: list[ComponentExplanation],
    facts: list[FactRow],
    claims: list[ReportClaim],
    banner: str,
) -> None:
    known = {fact.fact_id: fact for fact in facts}
    sentences: dict[str, list[str]] = {}
    for claim in claims:
        component = claim.subject_scope.get("component")
        if component:
            sentences.setdefault(component, []).append(escape(claim.text))
    rows = []
    for explanation in explanations:
        score = format_value(known[explanation.triage_fact_id])
        explanation_html = "<br>".join(sentences.get(explanation.component, []))
        examples = ", ".join(f"<code>{escape(record_id)}</code>" for record_id in explanation.example_record_ids)
        band = escape(explanation.band)
        rows.append(
            f"<tr><td>{escape(explanation.component)}</td><td class=\"{band}\">{band}</td>"
            f"<td>{score}</td><td>{explanation_html}</td><td>{examples}</td></tr>"
        )
    page = PAGE.format(banner=escape(banner), snapshot_id=escape(snapshot_id), rows="\n".join(rows))
    path.write_text(page, encoding="utf-8")
