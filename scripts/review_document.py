"""Approve ingested document chunks and publish them as an immutable corpus snapshot.

Approve:  uv run --no-project --with-requirements requirements-dev.txt python scripts/review_document.py approve outputs/documents/MAN-1/r1/DA-... --reviewer "A. Engineer" --reason "checked against the manual" --asset-model PX-100 --component seal
Publish:  uv run --no-project --with-requirements requirements-dev.txt python scripts/review_document.py publish outputs/documents/MAN-1/r1/DA-... --asset PUMP-SYN-01=PX-100 --out outputs/corpus/pump-v1.json
Serve it: scripts/serve_hosted.py --corpus outputs/corpus/pump-v1.json
Only a summary is printed, never document text.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.documents.corpus import publish_corpus, review_artifact  # noqa: E402


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    approve = commands.add_parser("approve", help="record a review of one ingested artifact")
    approve.add_argument("artifact_directory", type=Path)
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--reason", required=True)
    approve.add_argument("--asset-model", required=True)
    approve.add_argument("--component", required=True)
    approve.add_argument("--passages", nargs="+", help="approve only these passage ids (default: all chunks)")
    approve.add_argument("--corrections", type=Path, help='JSON file {"passage_id": "corrected text"}')
    approve.add_argument("--synthetic", action="store_true", help="label the review as synthetic demo review")
    publish = commands.add_parser("publish", help="publish reviewed artifacts as a corpus snapshot")
    publish.add_argument("artifact_directories", type=Path, nargs="+")
    publish.add_argument("--asset", action="append", required=True, help="asset_id=asset_model, repeatable")
    publish.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def approve(arguments) -> dict:
    corrections = json.loads(arguments.corrections.read_text(encoding="utf-8")) if arguments.corrections else None
    review = review_artifact(arguments.artifact_directory, arguments.reviewer, arguments.reason, arguments.asset_model,
                             arguments.component, arguments.passages, corrections, arguments.synthetic)
    return {"review_id": review.review_id, "document_id": review.document_id, "revision": review.revision,
            "approved_passages": len(review.approved_passage_ids), "corrections": len(review.corrections),
            "synthetic": review.synthetic}


def publish(arguments) -> dict:
    pairs = [asset.split("=", 1) for asset in arguments.asset]
    if any(len(pair) != 2 for pair in pairs):
        raise ValueError("--asset takes asset_id=asset_model")
    snapshot = publish_corpus(arguments.artifact_directories, dict(pairs), arguments.out)
    return {"corpus_version": snapshot["corpus"]["corpus_version"], "graph_version": snapshot["graph"]["graph_version"],
            "passages": len(snapshot["corpus"]["documents"]), "synthetic": snapshot["corpus"]["synthetic"],
            "output": str(arguments.out)}


def main() -> int:
    arguments = parse_arguments()
    try:
        summary = approve(arguments) if arguments.command == "approve" else publish(arguments)
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
