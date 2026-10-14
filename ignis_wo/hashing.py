"""Canonical JSON and content hashes, so identical inputs always hash the same."""

import hashlib
import json

from pydantic import BaseModel


def to_plain(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain(item) for key, item in value.items()}
    return value


def canonical_json(value) -> str:
    plain = to_plain(value)
    return json.dumps(plain, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(value) -> str:
    return sha256_text(canonical_json(value))


def short_id(prefix: str, *parts: str) -> str:
    digest = sha256_text("|".join(parts))
    return f"{prefix}-{digest[:12]}"
