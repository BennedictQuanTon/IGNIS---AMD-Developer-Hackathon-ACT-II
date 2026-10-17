"""#23 Stage 1 reader pilot: generate the synthetic pages, then read and score them.

Generate:  uv run --no-project --with-requirements requirements-dev.txt python scripts/benchmark_documents.py generate
Native:    ... python scripts/benchmark_documents.py read --reader native
MinerU:    uv run --env-file .env ... python scripts/benchmark_documents.py read --reader mineru
Each read runs twice; the second pass must be served from the parse cache with no OCR call.
A live job stops at 40 HTTP attempts or 30 minutes, and while 25% of the daily allowance remains.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.documents.cache import ParseCache  # noqa: E402
from ignis_wo.documents.ingest import ingest_document  # noqa: E402
from ignis_wo.evaluation.jobs import JobBudget  # noqa: E402
from ignis_wo.evaluation.reader_benchmark import FAMILIES, family_files, score_page  # noqa: E402
from ignis_wo.hashing import content_hash, sha256_bytes  # noqa: E402
from ignis_wo.hosted.ocr import OcrClient  # noqa: E402
from ignis_wo.hosted.pacing import RequestPacer  # noqa: E402
from ignis_wo.hosted.providers import client_from_environment  # noqa: E402
from ignis_wo.hosted.transport import ProviderError  # noqa: E402

PILOT = ROOT / "outputs" / "benchmarks" / "23" / "reader-pilot"


def generate() -> dict:
    PILOT.mkdir(parents=True, exist_ok=True)
    files = []
    for name, family in FAMILIES.items():
        for file_name, data, pages in family_files(name, family):
            (PILOT / file_name).write_bytes(data)
            files.append({"family": name, "split": family["split"], "file": file_name, "sha256": sha256_bytes(data),
                          "gold_pages": pages, "rights": "generated synthetic"})
    gold = {name: family["pages"] for name, family in FAMILIES.items()}
    lock = {"files": files, "gold_hash": content_hash(gold)}
    (PILOT / "lock.json").write_text(json.dumps(lock, indent=2), encoding="utf-8")
    return lock


def ocr_client(arguments, job: JobBudget, directory: Path) -> OcrClient | None:
    if arguments.reader != "mineru":
        return None
    model = arguments.model or os.environ.get("DOCUMENT_OCR_MODEL")
    if not model:
        raise SystemExit("set DOCUMENT_OCR_MODEL or pass --model")
    gateway = client_from_environment(pacer=RequestPacer(20, 1, arguments.allowance_reserve)).gateway
    gateway.budget = job
    return OcrClient(gateway, model, record_path=directory / "ocr-replay.jsonl")


def read_file(entry: dict, arguments, client, cache: ParseCache, directory: Path) -> list[dict]:
    family = FAMILIES[entry["family"]]
    document_id = entry["file"].rsplit(".", 1)[0]
    artifact, _, _ = ingest_document(PILOT / entry["file"], document_id, 1, arguments.reader, directory / "documents",
                                     ocr_client=client, cache=cache)
    rows = []
    returned = {text.index: text.markdown for text in artifact.pages}
    for artifact_page, gold_page in zip(artifact.requested_pages, entry["gold_pages"], strict=True):
        output = returned.get(artifact_page, "")
        row = {"family": entry["family"], "split": entry["split"], "file": entry["file"], "page": gold_page,
               "mode": artifact.mode, "status": artifact.status, "returned": artifact_page in returned,
               "latency_seconds": artifact.latency_seconds, "usage": artifact.usage}
        rows.append({**row, **score_page(family["pages"][gold_page], output)})
    return rows


def read(arguments) -> dict:
    lock = json.loads((PILOT / "lock.json").read_text(encoding="utf-8"))
    directory = PILOT / f"read-{arguments.reader}"
    directory.mkdir(parents=True, exist_ok=True)
    job = JobBudget(f"stage1-{arguments.reader}", arguments.max_attempts, arguments.max_seconds)
    client = ocr_client(arguments, job, directory)
    cache = ParseCache(directory / "cache")
    entries = [entry for entry in lock["files"] if arguments.reader == "mineru" or entry["file"].endswith(".pdf")]
    passes = {}
    for label in ("first", "repeat"):
        rows = []
        for entry in entries:
            try:
                rows.extend(read_file(entry, arguments, client, cache, directory))
            except ProviderError as error:
                rows.append({"family": entry["family"], "file": entry["file"], "error": error.kind,
                             "message": str(error)})
                if error.kind in ("job_budget", "credits", "auth"):
                    break
        passes[label] = rows
    for label, rows in passes.items():
        lines = [json.dumps(row, sort_keys=True) for row in rows]
        (directory / f"{label}.jsonl").write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    summary = {"reader": arguments.reader, "files": len(entries), "job": job.write(directory / "job"),
               "repeat_modes": sorted({row.get("mode", "error") for row in passes["repeat"]}),
               "errors": [row for row in passes["first"] if "error" in row]}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("generate")
    reading = commands.add_parser("read")
    reading.add_argument("--reader", choices=["native", "mineru"], required=True)
    reading.add_argument("--model")
    reading.add_argument("--max-attempts", type=int, default=40)
    reading.add_argument("--max-seconds", type=float, default=1800)
    reading.add_argument("--allowance-reserve", type=float, default=0.25)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    result = generate() if arguments.command == "generate" else read(arguments)
    print(json.dumps(result, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
