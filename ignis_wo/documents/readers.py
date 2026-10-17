"""Explicit document readers: local text for native PDFs, hosted OCR for scans and images.

The caller chooses the reader. There is no automatic quality detector and no silent fallback:
a native page without a text layer is reported, and the user can re-read it with OCR.
"""

import io
from pathlib import Path

import pypdf

from ignis_wo.documents.contracts import PageText, ReaderIdentity, SourceDocument
from ignis_wo.hashing import sha256_bytes

MEDIA_TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
STRUCTURED_SUFFIXES = {".csv", ".tsv", ".json", ".jsonl", ".xlsx"}
MAX_DOCUMENT_BYTES = 20_000_000


def source_for(path: Path, document_id: str, revision: int) -> tuple[SourceDocument, bytes]:
    suffix = path.suffix.lower()
    if suffix in STRUCTURED_SUFFIXES:
        raise ValueError(f"{suffix} files are work-order exports; use the structured import, not document reading")
    if suffix not in MEDIA_TYPES:
        raise ValueError(f"unsupported document type {suffix or '(none)'}; use PDF, PNG or JPEG")
    data = path.read_bytes()
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"{path.name} is {len(data)} bytes, over the {MAX_DOCUMENT_BYTES} byte limit")
    source = SourceDocument(document_id=document_id, revision=revision, file_name=path.name,
                            media_type=MEDIA_TYPES[suffix], sha256=sha256_bytes(data), size_bytes=len(data))
    return source, data


def page_count(source: SourceDocument, data: bytes) -> int:
    if source.media_type != "application/pdf":
        return 1
    return len(pypdf.PdfReader(io.BytesIO(data)).pages)


def requested_pages(selection: list[int] | None, count: int) -> list[int]:
    if selection is None:
        return list(range(count))
    outside = [index for index in selection if not 0 <= index < count]
    if outside:
        raise ValueError(f"pages {outside} are outside the document's {count} pages (zero-based)")
    return sorted(set(selection))


def native_identity() -> ReaderIdentity:
    return ReaderIdentity(reader="native-pypdf", config={"pypdf": pypdf.__version__})


def ocr_identity(ocr_client) -> ReaderIdentity:
    return ReaderIdentity(reader="mineru", model_id=ocr_client.model_id, config=ocr_client.config)


def read_native(source: SourceDocument, data: bytes, pages: list[int]) -> tuple[list[PageText], list[str]]:
    if source.media_type != "application/pdf":
        raise ValueError("images have no text layer; read them with --reader mineru")
    document = pypdf.PdfReader(io.BytesIO(data))
    texts, warnings = [], []
    for index in pages:
        text = document.pages[index].extract_text() or ""
        if not text.strip():
            warnings.append(f"page {index}: no text layer; read it with --reader mineru")
        texts.append(PageText(index=index, markdown=text))
    return texts, warnings


def read_with_ocr(source: SourceDocument, data: bytes, pages: list[int], ocr_client):
    """Returns (pages, missing page indices, OcrResult). Pages the reply leaves out are reported, not invented."""
    result = ocr_client.read(data, source.media_type, pages, source.sha256)
    texts = [PageText(index=page["index"], markdown=page["markdown"]) for page in result.pages]
    returned = {page.index for page in texts}
    missing = [index for index in pages if index not in returned]
    return texts, missing, result
