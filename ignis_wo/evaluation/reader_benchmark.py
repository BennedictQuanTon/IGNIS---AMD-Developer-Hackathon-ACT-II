"""Reader pilot for #23 Stage 1: generated synthetic pages with exact gold text, and page-level metrics.

Six document families, two pages each. Families 1-4 are development and 5-6 are held out; the two
pages of a family stay in the same split. Every page is generated here, so its gold text is exactly
what was drawn and the rights are ours. These pages are clean or lightly degraded synthetic renders,
not real factory scans, so results do not establish accuracy on real documents.

Normalization before CER/WER (declared): HTML tags and the Markdown markers # * _ | ` are removed and
whitespace is collapsed. Case, digits, decimal points and units are kept.
"""

import io
import random
import re

from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas

BANNER = "SYNTHETIC TEST DOCUMENT - NOT REAL FACTORY DATA"
TAGS = re.compile(r"<[^>]+>")
MARKERS = re.compile(r"[#*_|`]")
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def page(lines: list[str], critical: list[str], rows: list[list[str]] | None = None) -> dict:
    return {"lines": [BANNER, *lines], "critical": critical, "rows": rows or []}


def table_lines(rows: list[list[str]]) -> list[str]:
    return ["   ".join(row) for row in rows]


WORK_ORDERS = [["WO-101", "PX-100", "seal", "2.5"], ["WO-102", "PX-100", "bearing", "0.0"],
               ["WO-103", "PX-200", "seal", "1.0"], ["WO-104", "PX-100", "impeller", "4.25"]]
PARTS = [["P-7741", "Mechanical seal", "PX-100", "2"], ["P-7742", "Gland packing", "PX-100", "0"],
         ["P-8810", "Bearing 6305", "PX-200", "4"], ["P-9902", "Flush filter", "PX-100", "1"]]

FAMILIES = {
    "F1-manual": {"split": "dev", "kind": "pdf", "pages": [
        page(["Manual MAN-SYN-101 Revision 2 for pump model PX-100", "Section 3.2 Seal inspection",
              "Inspect the seal flush supply at 2.5 bar before further diagnosis.",
              "Do not replace the mechanical seal without expert approval.", "Gland bolt torque: 18.5 Nm."],
             ["MAN-SYN-101", "PX-100", "2.5 bar", "Do not replace", "18.5 Nm"]),
        page(["Section 4.1 Bearing checks for PX-100", "Bearing temperature above 85.0 degC requires inspection.",
              "No lubricant change is approved in this revision.",
              "Guidance for PX-200 must not be applied to PX-100."],
             ["85.0 degC", "No lubricant change", "PX-200 must not be applied"])]},
    "F2-table-pdf": {"split": "dev", "kind": "pdf", "pages": [
        page(["Work order summary WOS-22 for site SYN-A", "Work order   Model   Component   Downtime h",
              *table_lines(WORK_ORDERS[:2])], ["WOS-22", "WO-101", "WO-102", "2.5"],
             WORK_ORDERS[:2]),
        page(["Work order summary WOS-22 continued", "Work order   Model   Component   Downtime h",
              *table_lines(WORK_ORDERS[2:]), "Root cause is not confirmed for any work order."],
             ["WO-103", "WO-104", "4.25", "not confirmed"], WORK_ORDERS[2:])]},
    "F3-clean-scan": {"split": "dev", "kind": "image", "noise": 0.0, "pages": [
        page(["Handover note HN-301 for pump PX-100", "N1 Seal leakage observed. Flush line inspected.",
              "N2 No replacement performed.", "N3 Flush pressure measured at 1.8 bar."],
             ["HN-301", "No replacement performed", "1.8 bar"]),
        page(["Handover note HN-302 for pump PX-100", "N4 Root cause is not confirmed.",
              "N5 For PX-100 seal leakage, inspect the flush supply.", "N6 Bearing noise not reported."],
             ["HN-302", "not confirmed", "inspect the flush supply", "not reported"])]},
    "F4-noisy-scan": {"split": "dev", "kind": "image", "noise": 0.04, "rotate": 1.5, "pages": [
        page(["Inspection log IL-404 shift B", "Pump PX-100 vibration 7.1 mm/s at drive end.",
              "Seal chamber temperature 62.5 degC.", "No leak found at the gland."],
             ["IL-404", "7.1 mm/s", "62.5 degC", "No leak found"]),
        page(["Inspection log IL-405 shift C", "Pump PX-200 vibration 3.4 mm/s.",
              "Lubricant level normal.", "Do not restart without supervisor sign-off."],
             ["IL-405", "PX-200", "3.4 mm/s", "Do not restart"])]},
    "F5-table-image": {"split": "heldout", "kind": "image", "noise": 0.0, "grid": True, "pages": [
        page(["Spare parts list SPL-55", *table_lines(PARTS[:2])], ["SPL-55", "P-7741", "P-7742"], PARTS[:2]),
        page(["Spare parts list SPL-55 continued", *table_lines(PARTS[2:])], ["P-8810", "Bearing 6305", "P-9902"],
             PARTS[2:])]},
    "F6-diagram": {"split": "heldout", "kind": "diagram", "pages": [
        page(["Flush plan FP-11 for PX-100", "Flush line", "Seal chamber", "Flow 1.2 L/min"],
             ["FP-11", "Flush line", "Seal chamber", "1.2 L/min"]),
        page(["Drain plan DP-12 for PX-100", "Drain valve", "Leak detector", "Not connected to PX-200"],
             ["DP-12", "Drain valve", "Leak detector", "Not connected"])]},
}


def pdf_document(pages: list[dict]) -> bytes:
    buffer = io.BytesIO()
    drawing = canvas.Canvas(buffer)
    for content in pages:
        for index, line in enumerate(content["lines"]):
            drawing.drawString(60, 760 - 22 * index, line)
        drawing.showPage()
    drawing.save()
    return buffer.getvalue()


def text_image(content: dict, noise: float, rotate: float, grid: bool, seed: int) -> bytes:
    font = ImageFont.load_default(size=26)
    image = Image.new("L", (1400, 120 + 52 * len(content["lines"])), 255)
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(content["lines"]):
        draw.text((50, 40 + 52 * index), line, fill=0, font=font)
        if grid and index:
            draw.line((40, 32 + 52 * index, 1360, 32 + 52 * index), fill=90, width=2)
    pixels = image.load()
    generator = random.Random(seed)
    for _ in range(int(noise * image.width * image.height)):
        pixels[generator.randrange(image.width), generator.randrange(image.height)] = generator.choice((0, 255))
    if rotate:
        image = image.rotate(rotate, expand=True, fillcolor=255)
    return png(image)


def diagram_image(content: dict) -> bytes:
    font = ImageFont.load_default(size=26)
    image = Image.new("L", (1400, 700), 255)
    draw = ImageDraw.Draw(image)
    draw.text((50, 30), content["lines"][0], fill=0, font=font)
    draw.text((50, 80), content["lines"][1], fill=0, font=font)
    boxes = [(80, 250, 520, 400), (840, 250, 1300, 400)]
    for box, label in zip(boxes, content["lines"][2:4], strict=True):
        draw.rectangle(box, outline=0, width=4)
        draw.text((box[0] + 30, box[1] + 55), label, fill=0, font=font)
    draw.line((520, 325, 840, 325), fill=0, width=4)
    draw.polygon([(840, 325), (815, 310), (815, 340)], fill=0)
    draw.text((560, 270), content["lines"][4], fill=0, font=font)
    return png(image)


def png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def family_files(name: str, family: dict) -> list[tuple[str, bytes, list[int]]]:
    """Returns (file name, bytes, gold page numbers) for one family."""
    if family["kind"] == "pdf":
        return [(f"{name}.pdf", pdf_document(family["pages"]), [0, 1])]
    files = []
    for number, content in enumerate(family["pages"]):
        if family["kind"] == "diagram":
            data = diagram_image(content)
        else:
            data = text_image(content, family.get("noise", 0.0), family.get("rotate", 0.0), family.get("grid", False),
                              seed=number)
        files.append((f"{name}-p{number}.png", data, [number]))
    return files


def normalized(text: str) -> str:
    return " ".join(MARKERS.sub(" ", TAGS.sub(" ", text)).split())


def edit_distance(first: list, second: list) -> int:
    previous = list(range(len(second) + 1))
    for index, item in enumerate(first, 1):
        current = [index]
        for position, other in enumerate(second, 1):
            current.append(min(previous[position] + 1, current[-1] + 1, previous[position - 1] + (item != other)))
        previous = current
    return previous[-1]


def output_rows(text: str) -> list[str]:
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.IGNORECASE | re.DOTALL)
    return [normalized(row) for row in rows] + [normalized(line) for line in text.splitlines() if line.strip()]


def score_page(gold: dict, output: str) -> dict:
    expected = normalized(" ".join(gold["lines"]))
    produced = normalized(output)
    numbers = NUMBER.findall(expected)
    rows = output_rows(output)
    correct_rows = sum(any(all(cell in row for cell in gold_row) for row in rows) for gold_row in gold["rows"])
    return {
        "cer": round(edit_distance(list(expected), list(produced)) / len(expected), 4),
        "wer": round(edit_distance(expected.split(), produced.split()) / len(expected.split()), 4),
        "numbers_missing": [number for number in numbers if number not in NUMBER.findall(produced)],
        "critical_found": [field for field in gold["critical"] if field in produced],
        "critical_missing": [field for field in gold["critical"] if field not in produced],
        "table_rows": len(gold["rows"]), "table_rows_correct": correct_rows,
    }
