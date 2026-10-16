"""Model access behind one interface: fixture (gold), replay (recorded) or live (hosted AMD API)."""

import json
import threading
from pathlib import Path
from typing import Protocol

from ignis_wo.hashing import sha256_text
from ignis_wo.hosted.prompts import EXTRACTION_SCHEMA, ExtractionPrompt
from ignis_wo.hosted.transport import ChatClient, ProviderError, parse_json_content

TASK = "maintie-ie-v1"


class ExtractionAdapter(Protocol):
    mode: str
    model_id: str
    model_version: str

    def extract(self, text_norm: str): ...


class ReplayMiss(Exception):
    pass


def input_hash(text_norm: str) -> str:
    return sha256_text(f"{TASK}|{text_norm}")


def token_offsets(tokens: list[str]) -> list[int]:
    offsets = []
    position = 0
    for token in tokens:
        offsets.append(position)
        position += len(token) + 1
    return offsets


def gold_item_to_output(item: dict) -> tuple[str, dict]:
    """Converts MaintIE token spans (end exclusive) to character spans over the joined tokens."""
    tokens = item["tokens"]
    text_norm = " ".join(tokens)
    offsets = token_offsets(tokens)
    entities = []
    for index, entity in enumerate(item["entities"]):
        last_token = entity["end"] - 1
        start = offsets[entity["start"]]
        end = offsets[last_token] + len(tokens[last_token])
        span_text = " ".join(tokens[entity["start"]:entity["end"]])
        if text_norm[start:end] != span_text:
            raise ValueError(f"offset conversion failed for {span_text!r}")
        entities.append({"id": f"e{index}", "type": entity["type"], "start": start, "end": end, "text": span_text})
    relations = []
    for relation in item["relations"]:
        head = f"e{relation['head']}"
        tail = f"e{relation['tail']}"
        relations.append({"head": head, "tail": tail, "type": relation["type"]})
    return text_norm, {"entities": entities, "relations": relations}


class FixtureAdapter:
    mode = "fixture"
    model_id = "fixture-gold"

    def __init__(self, gold_items: list[dict], model_version: str = "maintie-gold"):
        self.model_version = model_version
        self.outputs = {}
        for item in gold_items:
            text_norm, output = gold_item_to_output(item)
            self.outputs[input_hash(text_norm)] = output

    def extract(self, text_norm: str):
        return self.outputs.get(input_hash(text_norm))


class ReplayAdapter:
    mode = "replay"

    def __init__(self, replay_path: Path, model_id: str, model_version: str):
        self.model_id = model_id
        self.model_version = model_version
        self.responses = {}
        self.failures = {}
        for line in replay_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row["model_id"] == model_id and row["model_version"] == model_version:
                self.responses[row["input_hash"]] = row["response"]
                self.failures.pop(row["input_hash"], None)
                if row.get("provider_error"):
                    self.failures[row["input_hash"]] = row["provider_error"]

    def extract(self, text_norm: str):
        """A record that failed live fails again the same way, so replay reproduces the run."""
        key = input_hash(text_norm)
        if key not in self.responses:
            raise ReplayMiss(f"no recorded response for input {key[:12]} and {self.model_id}@{self.model_version}")
        failure = self.failures.get(key)
        if failure:
            raise ProviderError(failure["kind"], f"replayed: {failure['message']}")
        return self.responses[key]


def is_index(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def anchored_token_span(entity: dict, tokens: list[str]) -> tuple[int, int] | None:
    """Finds the echoed span text as an exact token sequence, nearest the model's start index."""
    words = str(entity.get("text") or "").split()
    if not words:
        return None
    width = len(words)
    starts = [index for index in range(len(tokens) - width + 1) if tokens[index:index + width] == words]
    if not starts:
        return None
    hint = entity["start_token"] if is_index(entity.get("start_token")) else 0
    best = min(starts, key=lambda start: (abs(start - hint), start))
    return best, best + width


def token_span(entity: dict, tokens: list[str]) -> tuple[int | None, int | None, bool]:
    """Returns (start, end, reanchored). The echoed text wins when it disagrees with the indices."""
    start_token, end_token = entity.get("start_token"), entity.get("end_token")
    declared = is_index(start_token) and is_index(end_token) and 0 <= start_token < end_token <= len(tokens)
    text = entity.get("text")
    if declared and (not text or " ".join(tokens[start_token:end_token]) == text):
        return start_token, end_token, False
    anchored = anchored_token_span(entity, tokens)
    if anchored:
        return anchored[0], anchored[1], True
    if declared:
        return start_token, end_token, False
    return None, None, False


def token_entity_to_characters(entity, tokens: list[str], offsets: list[int]) -> tuple[dict, bool]:
    """Spans that cannot be placed become -1 offsets so the validator rejects them with a reason."""
    if not isinstance(entity, dict):
        return entity, False
    start_token, end_token, reanchored = token_span(entity, tokens)
    if start_token is None:
        unplaced = {"id": entity.get("id"), "type": entity.get("type"), "start": -1, "end": -1,
                    "text": entity.get("text", "")}
        return unplaced, False
    start = offsets[start_token]
    end = offsets[end_token - 1] + len(tokens[end_token - 1])
    text = entity.get("text") or " ".join(tokens[start_token:end_token])
    placed = {"id": entity.get("id"), "type": entity.get("type"), "start": start, "end": end, "text": text}
    return placed, reanchored


def token_spans_to_output(raw: dict, text_norm: str) -> tuple[dict, int]:
    """Converts the model's token spans (end exclusive) to character spans; also counts re-anchored spans."""
    tokens = text_norm.split(" ")
    offsets = token_offsets(tokens)
    converted = [token_entity_to_characters(entity, tokens, offsets) for entity in raw.get("entities") or []]
    entities = [entity for entity, _ in converted]
    reanchored = sum(flag for _, flag in converted)
    return {"entities": entities, "relations": raw.get("relations") or []}, reanchored


def require_lists(raw: dict) -> None:
    for key in ("entities", "relations"):
        if raw.get(key) is not None and not isinstance(raw[key], list):
            raise ProviderError("invalid_response", f"'{key}' is not a list")


class LiveAdapter:
    """Hosted extraction through the AMD chat API. The model returns token spans; code converts them."""

    mode = "live"

    def __init__(
        self,
        client: ChatClient,
        model_id: str,
        prompt: ExtractionPrompt | None = None,
        output_mode: str = "json_object",
        reasoning_effort: str | None = "low",
        max_tokens: int = 4096,
        record_path: Path | None = None,
    ):
        self.client = client
        self.model_id = model_id
        self.prompt = prompt or ExtractionPrompt()
        self.output_mode = output_mode
        self.reasoning_effort = reasoning_effort
        self.max_tokens = max_tokens
        self.record_path = record_path
        self.model_version = f"{self.prompt.prompt_id}+{output_mode}+{reasoning_effort or 'default'}"
        self.lock = threading.Lock()

    def extract(self, text_norm: str):
        response, _, _ = self.extract_with_result(text_norm)
        return response

    def extract_with_result(self, text_norm: str):
        schema = EXTRACTION_SCHEMA if self.output_mode == "json_schema" else None
        messages = self.prompt.messages(text_norm)
        try:
            result = self.client.complete(self.model_id, messages, self.output_mode, schema, self.reasoning_effort,
                                          self.max_tokens)
            raw = parse_json_content(result.content)
            require_lists(raw)
        except ProviderError as error:
            if error.record_level:
                self.record_failure(text_norm, error)
            raise
        response, reanchored = token_spans_to_output(raw, text_norm)
        self.record(text_norm, raw, response, result, reanchored)
        return response, result, reanchored

    def record_failure(self, text_norm: str, error: ProviderError) -> None:
        message = str(error).removeprefix(f"{error.kind}: ")
        self.write_row({**self.row_identity(text_norm), "response": None,
                        "provider_error": {"kind": error.kind, "message": message}})

    def row_identity(self, text_norm: str) -> dict:
        return {"input_hash": input_hash(text_norm), "model_id": self.model_id, "model_version": self.model_version,
                "prompt_id": self.prompt.prompt_id, "output_mode": self.output_mode}

    def record(self, text_norm: str, raw: dict, response: dict, result, reanchored: int) -> None:
        row = {
            **self.row_identity(text_norm),
            "raw": raw,
            "response": response,
            "spans_reanchored": reanchored,
            "finish_reason": result.finish_reason,
            "usage": result.usage,
            "latency_seconds": result.latency_seconds,
            "request_parameters": result.request_parameters,
        }
        self.write_row(row)

    def write_row(self, row: dict) -> None:
        if self.record_path is None:
            return
        with self.lock, self.record_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(row, sort_keys=True) + "\n")
