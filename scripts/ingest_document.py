"""Read one PDF or image into page-linked, unreviewed candidate evidence under outputs/documents/.

Native text PDF:  uv run --no-project --with-requirements requirements-dev.txt python scripts/ingest_document.py manual.pdf --document-id MAN-PUMP-A --revision 1 --reader native
Scan or image:    uv run --env-file .env --no-project --with-requirements requirements-dev.txt python scripts/ingest_document.py scan.png --document-id SCAN-1 --revision 1 --reader mineru
The OCR model comes from DOCUMENT_OCR_MODEL. Identical bytes, pages and reader settings are served
from the parse cache with no OCR call. Output text is never printed, only the artifact summary.
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
from ignis_wo.hosted.ocr import OcrClient  # noqa: E402
from ignis_wo.hosted.providers import client_from_environment  # noqa: E402
from ignis_wo.hosted.transport import ProviderError  # noqa: E402


def parse_pages(text: str | None) -> list[int] | None:
    """Zero-based pages: "0-3" or "0,2,5"."""
    if not text:
        return None
    if "-" in text:
        first, last = text.split("-", 1)
        return list(range(int(first), int(last) + 1))
    return [int(part) for part in text.split(",")]


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--revision", type=int, required=True)
    parser.add_argument("--reader", choices=["native", "mineru"], required=True)
    parser.add_argument("--pages", help='zero-based pages, "0-3" or "0,2"; all pages when omitted')
    parser.add_argument("--model", default=os.environ.get("DOCUMENT_OCR_MODEL"), help="OCR model for --reader mineru")
    parser.add_argument("--mode", choices=["live", "replay"], default="live")
    parser.add_argument("--record", type=Path, help="append live OCR replies to this replay file")
    parser.add_argument("--replay", type=Path, help="recorded OCR replies for --mode replay")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "outputs" / "document-cache")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "documents")
    return parser.parse_args()


def ocr_client_for(arguments) -> OcrClient | None:
    if arguments.reader != "mineru":
        return None
    if not arguments.model:
        raise SystemExit("set DOCUMENT_OCR_MODEL in .env or pass --model to read with MinerU")
    if arguments.mode == "replay":
        if not arguments.replay or not arguments.replay.exists():
            raise SystemExit("--mode replay needs an existing --replay file")
        return OcrClient(None, arguments.model, replay_path=arguments.replay)
    return OcrClient(client_from_environment().gateway, arguments.model, record_path=arguments.record)


def main() -> int:
    arguments = parse_arguments()
    ocr_client = ocr_client_for(arguments)
    try:
        artifact, chunks, directory = ingest_document(
            arguments.file, arguments.document_id, arguments.revision, arguments.reader, arguments.out,
            parse_pages(arguments.pages), ocr_client, ParseCache(arguments.cache_dir))
    except ValueError as error:
        raise SystemExit(str(error)) from None
    except ProviderError as error:
        print(f"document reading failed ({error.kind}); no evidence was produced", file=sys.stderr)
        return 1
    summary = {"artifact_id": artifact.artifact_id, "status": artifact.status, "mode": artifact.mode,
               "reader": artifact.reader.reader, "model_id": artifact.reader.model_id,
               "requested_pages": artifact.requested_pages, "missing_pages": artifact.missing_pages,
               "warnings": artifact.warnings, "chunks": len(chunks), "review_status": artifact.review_status,
               "output": str(directory)}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
