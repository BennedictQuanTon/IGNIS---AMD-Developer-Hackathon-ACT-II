"""Shared synthetic inputs for the pipeline tests (no network, no MaintIE download)."""

import csv
import io
import json
import tempfile
from pathlib import Path

from reportlab.pdfgen import canvas

from ignis_wo.contracts import ComponentCriticality, Snapshot
from ignis_wo.extraction.adapters import FixtureAdapter
from ignis_wo.extraction.suggest import suggest_all
from ignis_wo.hosted.prompts import ExtractionPrompt, select_examples
from ignis_wo.ingest.mapping import build_records, confirm_mapping, propose_mapping
from ignis_wo.ingest.registry import parse_file
from ignis_wo.review import accept_all
from ignis_wo.snapshot import build_snapshot

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "maintie_sample.json"
COLUMNS = ["WO #", "Equipment ID", "Reported Date", "Work Order Description", "Downtime (h)"]


def pdf_bytes(page_texts: list[str]) -> bytes:
    buffer = io.BytesIO()
    drawing = canvas.Canvas(buffer)
    for text in page_texts:
        if text:
            drawing.drawString(72, 720, text)
        drawing.showPage()
    drawing.save()
    return buffer.getvalue()


def sample_items() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def frozen_config_for(items: list[dict], model_id: str = "m") -> dict:
    """A frozen extraction configuration built from the sample items instead of MaintIE."""
    prompt = ExtractionPrompt(select_examples(items, 2))
    return {"model_id": model_id, "example_count": 2, "output_mode": "json_object", "reasoning_effort": None,
            "max_tokens": 4096, "budget_fallback": False, "prompt_id": prompt.prompt_id,
            "scored_as": {"prompt_id": prompt.legacy_prompt_id()}}


def sample_adapter() -> FixtureAdapter:
    return FixtureAdapter(sample_items(), model_version="sample")


def build_sample_records(directory: Path | None = None) -> list:
    with tempfile.TemporaryDirectory() as temporary:
        csv_path = write_sample_csv(Path(directory or temporary) / "export.csv")
        source_file, rows = parse_file(csv_path)
    proposal = propose_mapping(COLUMNS)
    revision = confirm_mapping(proposal, "tester", "test")
    records, _ = build_records(source_file, rows, revision)
    return records


def sample_snapshot(directory: Path, criticalities: list[ComponentCriticality] | None = None) -> Snapshot:
    records = build_sample_records(directory)
    suggestions = suggest_all(records, sample_adapter())
    annotations = accept_all(suggestions, "tester", "test")
    versions = {"severity": "severity-v1", "triage": "triage-v1"}
    return build_snapshot(records, annotations, criticalities or [], versions)


def write_sample_csv(path: Path) -> Path:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        for index, item in enumerate(sample_items(), start=1):
            text = " ".join(item["tokens"])
            writer.writerow([f"WO-{index}", "HT-101", f"2025-01-{index:02d}", text, "1.5"])
    return path
