"""Typed records for document reading. Everything a reader produces starts as unreviewed candidate evidence."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PARSER_VERSION = "document-parse-v1"
SAFE_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"


class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_id: str = Field(pattern=SAFE_ID)
    revision: int = Field(ge=1)
    file_name: str
    media_type: Literal["application/pdf", "image/png", "image/jpeg"]
    sha256: str
    size_bytes: int


class ReaderIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    reader: Literal["native-pypdf", "mineru"]
    model_id: str | None = None
    config: dict = {}
    parser_version: str = PARSER_VERSION


class PageText(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    index: int = Field(ge=0)
    markdown: str


class DocumentArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    artifact_id: str
    source: SourceDocument
    reader: ReaderIdentity
    requested_pages: list[int]
    processed_pages: list[int]
    missing_pages: list[int]
    pages: list[PageText]
    mode: Literal["native", "hosted_live", "hosted_replay", "cache"]
    status: Literal["complete", "partial"]
    warnings: list[str] = []
    latency_seconds: float | None = None
    usage: dict = {}
    review_status: Literal["unreviewed"] = "unreviewed"


class CandidateChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    passage_id: str
    document_id: str
    revision: int
    artifact_id: str
    source_sha256: str
    page_index: int
    chunk_index: int
    text: str
    reader: ReaderIdentity
    review_status: Literal["unreviewed"] = "unreviewed"
