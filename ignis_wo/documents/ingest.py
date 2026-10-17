"""Reads one evidence document into a cached, page-linked artifact and unreviewed candidate chunks.

Nothing here approves evidence or feeds retrieval: the output waits for document review.
"""

import json
from pathlib import Path

from ignis_wo.documents.cache import ParseCache, artifact_key
from ignis_wo.documents.chunks import chunk_artifact
from ignis_wo.documents.contracts import DocumentArtifact
from ignis_wo.documents.readers import (
    native_identity,
    ocr_identity,
    page_count,
    read_native,
    read_with_ocr,
    requested_pages,
    source_for,
)


def fresh_artifact(artifact_id, source, data, pages, reader, identity, ocr_client) -> DocumentArtifact:
    common = {"artifact_id": artifact_id, "source": source, "reader": identity, "requested_pages": pages}
    if reader == "native":
        texts, warnings = read_native(source, data, pages)
        return DocumentArtifact(**common, processed_pages=pages, missing_pages=[], pages=texts, mode="native",
                                status="complete", warnings=warnings)
    texts, missing, result = read_with_ocr(source, data, pages, ocr_client)
    warnings = [f"page {index}: not returned by OCR" for index in missing]
    return DocumentArtifact(**common, processed_pages=[page.index for page in texts], missing_pages=missing,
                            pages=texts, mode=ocr_client.mode, status="partial" if missing else "complete",
                            warnings=warnings, latency_seconds=result.latency_seconds, usage=result.usage)


def write_outputs(directory: Path, data: bytes, artifact: DocumentArtifact, chunks) -> None:
    """A reviewed directory is never given different text: the review would then approve text nobody read."""
    lines = [json.dumps(chunk.model_dump(mode="json"), sort_keys=True) for chunk in chunks]
    content = "".join(line + "\n" for line in lines)
    chunks_path = directory / "chunks.jsonl"
    reviewed = (directory / "review.json").exists() and chunks_path.exists()
    if reviewed and chunks_path.read_text(encoding="utf-8") != content:
        raise ValueError(f"{directory} was reviewed and the new reading differs; "
                         "ingest it as a new revision or review it again")
    directory.mkdir(parents=True, exist_ok=True)
    suffix = Path(artifact.source.file_name).suffix.lower()
    (directory / f"original{suffix}").write_bytes(data)
    (directory / "artifact.json").write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    chunks_path.write_text(content, encoding="utf-8")


def ingest_document(path: Path, document_id: str, revision: int, reader: str, output_root: Path,
                    pages: list[int] | None = None, ocr_client=None, cache: ParseCache | None = None):
    """Returns (artifact, chunks, output directory). A cache hit makes no OCR call."""
    if reader == "mineru" and ocr_client is None:
        raise ValueError("the mineru reader needs an OCR client (set DOCUMENT_OCR_MODEL)")
    source, data = source_for(path, document_id, revision)
    selected = requested_pages(pages, page_count(source, data))
    identity = native_identity() if reader == "native" else ocr_identity(ocr_client)
    artifact_id = artifact_key(source.sha256, selected, identity)
    cached = cache.load(artifact_id) if cache else None
    if cached:
        artifact = cached.model_copy(update={"source": source, "mode": "cache", "latency_seconds": None, "usage": {}})
    else:
        artifact = fresh_artifact(artifact_id, source, data, selected, reader, identity, ocr_client)
        if cache:
            cache.store(artifact)
    chunks = chunk_artifact(artifact)
    directory = output_root / document_id / f"r{revision}" / artifact_id[:15]
    write_outputs(directory, data, artifact, chunks)
    return artifact, chunks, directory
