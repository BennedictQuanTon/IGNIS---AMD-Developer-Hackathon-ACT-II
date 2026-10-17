"""Document OCR through the AMD `/ocr` endpoint (MinerU2.5-Pro), sharing the chat Gateway.

Documented request and response: https://amd-aim.github.io/radeon-cloud-docs/models/mineru2-5-pro/
Only `model`, `document`, `pages` and `id` are sent; chat-only parameters never reach `/ocr`.
The page Markdown is untrusted data: it is checked for shape here and never interpreted.
"""

import base64
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path

from ignis_wo.extraction.adapters import ReplayMiss
from ignis_wo.hashing import sha256_text
from ignis_wo.hosted.transport import ProviderError

TASK = "document-ocr-v1"


@dataclass(frozen=True)
class OcrResult:
    pages: list[dict]
    usage: dict
    latency_seconds: float
    attempts: int
    request_parameters: dict = field(default_factory=dict)


def document_field(media_type: str, data: bytes) -> dict:
    url = f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"
    if media_type == "application/pdf":
        return {"type": "document_url", "document_url": url}
    return {"type": "image_url", "image_url": url}


def checked_page(page, requested: set[int]) -> dict:
    if not isinstance(page, dict):
        raise ProviderError("invalid_response", "a page is not an object")
    index, markdown = page.get("index"), page.get("markdown")
    if not isinstance(index, int) or isinstance(index, bool) or not isinstance(markdown, str):
        raise ProviderError("invalid_response", "a page lacks an integer index or Markdown text")
    if index not in requested:
        raise ProviderError("invalid_response", f"page {index} was not requested")
    return {"index": index, "markdown": markdown}


def checked_pages(reply, requested: list[int]) -> list[dict]:
    pages = reply.get("pages") if isinstance(reply, dict) else None
    if not isinstance(pages, list):
        raise ProviderError("invalid_response", "reply has no pages list")
    if not pages:
        raise ProviderError("empty_output", "the reply contained no pages")
    checked = [checked_page(page, set(requested)) for page in pages]
    indices = [page["index"] for page in checked]
    if len(indices) != len(set(indices)):
        raise ProviderError("invalid_response", "a page index was returned twice")
    return sorted(checked, key=lambda page: page["index"])


def load_responses(replay_path: Path) -> dict[str, dict]:
    rows = [json.loads(line) for line in replay_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {row["key"]: row for row in rows}


class OcrClient:
    """Live reads go through the shared Gateway; replay serves recorded replies without any call."""

    def __init__(self, gateway, model_id: str, timeout_seconds: float = 600, max_body_bytes: int = 30_000_000,
                 record_path: Path | None = None, replay_path: Path | None = None):
        self.gateway = gateway
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.max_body_bytes = max_body_bytes
        self.record_path = record_path
        self.responses = load_responses(replay_path) if replay_path else None
        self.mode = "hosted_replay" if replay_path else "hosted_live"
        self.config = {"endpoint": "/ocr", "include_image_base64": False}
        self.lock = threading.Lock()

    def request_key(self, source_sha256: str, pages: list[int]) -> str:
        parts = [TASK, self.model_id, json.dumps(self.config, sort_keys=True), source_sha256, json.dumps(pages)]
        return sha256_text("|".join(parts))

    def read(self, data: bytes, media_type: str, pages: list[int], source_sha256: str) -> OcrResult:
        key = self.request_key(source_sha256, pages)
        if self.responses is not None:
            return self.replayed(key, pages)
        body = {"model": self.model_id, "document": document_field(media_type, data), "pages": pages,
                "id": f"IGNIS-{source_sha256[:12]}"}
        reply, _, latency, attempts = self.gateway.send("POST", "/ocr", body, self.timeout_seconds,
                                                        self.max_body_bytes)
        checked = checked_pages(reply, pages)
        usage = reply.get("usage_info") or {}
        parameters = {"model": self.model_id, "pages": pages, "document_type": body["document"]["type"]}
        result = OcrResult(checked, usage, round(latency, 3), attempts, parameters)
        self.record(key, result)
        return result

    def replayed(self, key: str, pages: list[int]) -> OcrResult:
        row = self.responses.get(key)
        if row is None:
            raise ReplayMiss(f"no recorded OCR reply for pages {pages} with {self.model_id}")
        return OcrResult(row["pages"], row["usage"], row["latency_seconds"], 0, row["request_parameters"])

    def record(self, key: str, result: OcrResult) -> None:
        if self.record_path is None:
            return
        row = {"key": key, "task": TASK, "model_id": self.model_id, "pages": result.pages, "usage": result.usage,
               "latency_seconds": result.latency_seconds, "request_parameters": result.request_parameters}
        with self.lock, self.record_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(row, sort_keys=True) + "\n")
