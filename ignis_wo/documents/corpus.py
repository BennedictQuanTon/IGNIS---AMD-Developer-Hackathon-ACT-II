"""Explicit document review and immutable corpus snapshots for retrieval.

A reviewer approves chunks of one artifact for one asset model and component. Publishing turns
approved reviews into a versioned corpus plus applicability map that retrieval can be given.
Raw reader output in chunks.jsonl is never rewritten; corrections are stored beside it.
"""

import datetime
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ignis_wo.documents.contracts import CandidateChunk, DocumentArtifact
from ignis_wo.hashing import content_hash, sha256_text


class DocumentReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    review_id: str
    reviewer: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    reviewed_at: str
    synthetic: bool
    artifact_id: str
    document_id: str
    revision: int
    source_sha256: str
    asset_model: str = Field(min_length=1)
    component: str = Field(min_length=1)
    approved_passage_ids: list[str] = Field(min_length=1)
    approved_text_sha256: dict[str, str]
    corrections: dict[str, str] = {}


def read_artifact(directory: Path) -> tuple[DocumentArtifact, list[CandidateChunk]]:
    artifact = DocumentArtifact.model_validate_json((directory / "artifact.json").read_text(encoding="utf-8"))
    lines = (directory / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    chunks = [CandidateChunk.model_validate_json(line) for line in lines if line.strip()]
    return artifact, chunks


def review_artifact(directory: Path, reviewer: str, reason: str, asset_model: str, component: str,
                    passage_ids: list[str] | None = None, corrections: dict[str, str] | None = None,
                    synthetic: bool = False) -> DocumentReview:
    if not reviewer.strip() or not reason.strip():
        raise ValueError("a reviewer and a reason are required")
    artifact, chunks = read_artifact(directory)
    if artifact.status != "complete":
        raise ValueError(f"artifact is {artifact.status} (missing pages {artifact.missing_pages}); "
                         "re-read the missing pages first")
    known = [chunk.passage_id for chunk in chunks]
    approved = known if passage_ids is None else passage_ids
    if not approved:
        raise ValueError("approve at least one passage")
    unknown = sorted(set(approved) - set(known))
    if unknown:
        raise ValueError(f"unknown passages {unknown}")
    corrections = corrections or {}
    unapproved = sorted(set(corrections) - set(approved))
    if unapproved:
        raise ValueError(f"corrections given for passages that are not approved: {unapproved}")
    reviewed_text = {chunk.passage_id: sha256_text(chunk.text) for chunk in chunks if chunk.passage_id in approved}
    reviewed_at = datetime.datetime.now(datetime.UTC).isoformat()
    review = DocumentReview(
        review_id="DR-" + content_hash([artifact.artifact_id, reviewer, reviewed_at])[:12], reviewer=reviewer,
        reason=reason, reviewed_at=reviewed_at, synthetic=synthetic, artifact_id=artifact.artifact_id,
        document_id=artifact.source.document_id, revision=artifact.source.revision,
        source_sha256=artifact.source.sha256, asset_model=asset_model, component=component,
        approved_passage_ids=approved, approved_text_sha256=reviewed_text, corrections=corrections)
    (directory / "review.json").write_text(review.model_dump_json(indent=2), encoding="utf-8")
    return review


def corpus_item(chunk: CandidateChunk, review: DocumentReview, file_name: str) -> dict:
    corrected = chunk.passage_id in review.corrections
    return {
        "document_id": chunk.document_id, "passage_id": chunk.passage_id, "version": str(chunk.revision),
        "asset_model": review.asset_model, "component": review.component, "status": "approved",
        "reviewer": review.reviewer, "review_id": review.review_id, "source_id": file_name,
        "location": f"page {chunk.page_index + 1} / chunk {chunk.chunk_index + 1}",
        "source_sha256": chunk.source_sha256, "artifact_id": chunk.artifact_id,
        "reader": chunk.reader.model_dump(mode="json"), "corrected": corrected,
        "text": review.corrections[chunk.passage_id] if corrected else chunk.text,
    }


def reviewed_items(directory: Path) -> tuple[DocumentReview, list[dict]]:
    review_path = directory / "review.json"
    if not review_path.exists():
        raise ValueError(f"{directory} has no review.json; approve it first")
    review = DocumentReview.model_validate_json(review_path.read_text(encoding="utf-8"))
    artifact, chunks = read_artifact(directory)
    if artifact.artifact_id != review.artifact_id:
        raise ValueError(f"{directory}: review.json belongs to another artifact")
    approved = [chunk for chunk in chunks if chunk.passage_id in set(review.approved_passage_ids)]
    current = {chunk.passage_id: sha256_text(chunk.text) for chunk in approved}
    if current != review.approved_text_sha256:
        raise ValueError(f"{directory}: the chunk text differs from the reviewed text; review it again")
    return review, [corpus_item(chunk, review, artifact.source.file_name) for chunk in approved]


def applicability_graph(reviews: list[DocumentReview], assets: dict[str, str]) -> dict:
    graph_assets = {}
    for asset_id, asset_model in sorted(assets.items()):
        components = {}
        for review in reviews:
            if review.asset_model == asset_model:
                components.setdefault(review.component, []).append(review.document_id)
        if not components:
            raise ValueError(f"no review covers asset {asset_id} (model {asset_model})")
        graph_assets[asset_id] = {"model": asset_model, "components": components}
    graph = {"assets": graph_assets, "approval_status": "reviewed document corpus"}
    return {"graph_version": "graph-" + content_hash(graph)[:12], **graph}


def publish_corpus(review_directories: list[Path], assets: dict[str, str], output_path: Path) -> dict:
    """Writes {"corpus", "graph"} once; an existing snapshot is never overwritten."""
    if output_path.exists():
        raise ValueError(f"{output_path} exists; corpus snapshots are immutable, choose a new name")
    reviews, items = [], []
    for directory in review_directories:
        review, reviewed = reviewed_items(directory)
        reviews.append(review)
        items.extend(reviewed)
    document_ids = [review.document_id for review in reviews]
    repeated = sorted({document_id for document_id in document_ids if document_ids.count(document_id) > 1})
    if repeated:
        raise ValueError(f"publish one revision per document; repeated: {repeated}")
    synthetic = any(review.synthetic for review in reviews)
    corpus = {"documents": items, "synthetic": synthetic,
              "approval_status": "SYNTHETIC review" if synthetic else "reviewed documents"}
    snapshot = {"corpus": {"corpus_version": "corpus-" + content_hash(corpus)[:12], **corpus},
                "graph": applicability_graph(reviews, assets)}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    return snapshot


def load_corpus_snapshot(path: Path) -> tuple[dict, dict]:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    corpus, graph = snapshot["corpus"], snapshot["graph"]
    if not corpus.get("corpus_version") or not graph.get("graph_version"):
        raise ValueError(f"{path} is not a corpus snapshot")
    return corpus, graph
