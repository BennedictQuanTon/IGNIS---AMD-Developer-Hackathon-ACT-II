"""Build a seeded, clearly synthetic work-order export from MaintIE train-split texts.

The texts are real MaintIE lines; asset ids, dates, downtime and priority are invented
and marked synthetic. Output goes to the gitignored data/demo/ folder.
"""

import argparse
import csv
import datetime
import random
import sys
from pathlib import Path

from openpyxl import Workbook

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from ignis_wo.evaluation.maintie import load_verified_splits  # noqa: E402

COLUMNS = ["WO #", "Equipment ID", "Reported Date", "Work Order Description", "Downtime (h)", "Priority", "Data note"]
ASSETS = ["HT-101", "HT-102", "LD-201", "LD-202", "CV-301", "PM-401"]
PRIORITIES = ["P1", "P2", "P3"]


def build_rows(texts: list[str], seed: int) -> list[list]:
    generator = random.Random(seed)
    start_date = datetime.date(2025, 1, 1)
    rows = []
    for index, text in enumerate(texts, start=1):
        reported = start_date + datetime.timedelta(days=generator.randrange(365))
        downtime = round(generator.uniform(0, 12), 1)
        asset = generator.choice(ASSETS)
        priority = generator.choice(PRIORITIES)
        rows.append([f"WO-{index:05d}", asset, reported.isoformat(), text, downtime, priority, "SYNTHETIC fields"])
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, default=Path("data/maintie/gold_release.json"))
    parser.add_argument("--out", type=Path, default=Path("data/demo"))
    parser.add_argument("--rows", type=int, default=400)
    parser.add_argument("--seed", type=int, default=7)
    arguments = parser.parse_args()

    train_items = load_verified_splits(arguments.gold)["train"]
    texts = [" ".join(item["tokens"]) for item in train_items]
    sampler = random.Random(arguments.seed)
    chosen = sampler.sample(texts, min(arguments.rows, len(texts)))
    rows = build_rows(chosen, arguments.seed)

    arguments.out.mkdir(parents=True, exist_ok=True)
    csv_path = arguments.out / "export.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Work orders"
    sheet.append(COLUMNS)
    for row in rows:
        sheet.append(row)
    xlsx_path = arguments.out / "export.xlsx"
    workbook.save(xlsx_path)
    print(f"wrote {len(rows)} synthetic-field rows to {csv_path} and {xlsx_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
