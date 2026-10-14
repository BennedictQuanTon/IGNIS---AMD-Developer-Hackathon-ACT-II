"""Model access behind one interface: fixture (gold), replay (recorded) or live (vLLM)."""

import json
import urllib.request
from pathlib import Path
from typing import Protocol

from ignis_wo.contracts import ExtractionOutput
from ignis_wo.hashing import sha256_text

TASK = "maintie-ie-v1"
SYSTEM_PROMPT = (
    "Extract MaintIE entities and relations from the maintenance work order. "
    "Return JSON that matches the schema. Entity start and end are character offsets "
    "into the input text, end exclusive, and entity text must equal that slice."
)


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
        for line in replay_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row["model_id"] == model_id and row["model_version"] == model_version:
                self.responses[row["input_hash"]] = row["response"]

    def extract(self, text_norm: str):
        key = input_hash(text_norm)
        if key not in self.responses:
            raise ReplayMiss(f"no recorded response for input {key[:12]} and {self.model_id}@{self.model_version}")
        return self.responses[key]


class LiveAdapter:
    mode = "live"

    def __init__(
        self,
        base_url: str,
        model_id: str,
        model_version: str,
        api_key: str | None = None,
        record_path: Path | None = None,
        timeout_seconds: float = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.model_version = model_version
        self.api_key = api_key
        self.record_path = record_path
        self.timeout_seconds = timeout_seconds

    def request_body(self, text_norm: str) -> dict:
        schema = ExtractionOutput.model_json_schema()
        return {
            "model": self.model_id,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text_norm},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "maintie_ie", "schema": schema},
            },
        }

    def extract(self, text_norm: str):
        body = json.dumps(self.request_body(text_norm)).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, headers=headers)
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            reply = json.loads(response.read())
        content = reply["choices"][0]["message"]["content"]
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = content
        self.record(text_norm, parsed)
        return parsed

    def record(self, text_norm: str, response) -> None:
        if self.record_path is None:
            return
        row = {
            "input_hash": input_hash(text_norm),
            "model_id": self.model_id,
            "model_version": self.model_version,
            "response": response,
        }
        with self.record_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(row, sort_keys=True) + "\n")
