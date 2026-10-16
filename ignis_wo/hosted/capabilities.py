"""Stage A: one tiny request per chat model and output mode, recorded as a capability matrix."""

import datetime

from ignis_wo.hosted.transport import STOP_KINDS, ProviderError, parse_json_content

PROBE_MESSAGES = [
    {"role": "system", "content": "Reply with a JSON object only."},
    {"role": "user", "content": 'Return this JSON object unchanged: {"status": "ok", "component": "pump"}'},
]
PROBE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["status", "component"],
    "properties": {"status": {"type": "string"}, "component": {"type": "string"}},
}


def probe_plan(models: list[dict]) -> list[tuple[str, str]]:
    plan = []
    for model in models:
        if not model.get("json_output"):
            continue
        plan.append((model["id"], "json_object"))
        if model.get("structured_outputs"):
            plan.append((model["id"], "json_schema"))
    return plan


def probe(client, model_id: str, output_mode: str, reasoning_effort: str, max_tokens: int) -> dict:
    row = {"model": model_id, "output_mode": output_mode, "reasoning_effort": reasoning_effort}
    schema = PROBE_SCHEMA if output_mode == "json_schema" else None
    try:
        result = client.complete(model_id, PROBE_MESSAGES, output_mode, schema, reasoning_effort, max_tokens)
    except ProviderError as error:
        row.update({"status": error.kind, "error": str(error), "http_status": error.status, "code": error.code})
        return row
    try:
        parsed = parse_json_content(result.content)
        row["status"] = "ok" if parsed.get("status") == "ok" else "unexpected_content"
    except ProviderError as error:
        row["status"] = error.kind
    row.update({"finish_reason": result.finish_reason, "returned_reasoning": bool(result.reasoning),
                "latency_seconds": result.latency_seconds, "attempts": result.attempts, "usage": result.usage,
                "rate_headers": result.rate_headers})
    return row


def capability_matrix(client, max_requests: int = 20, reasoning_effort: str = "low", max_tokens: int = 1024) -> dict:
    models = client.list_models()
    probes = []
    for model_id, output_mode in probe_plan(models)[:max_requests]:
        row = probe(client, model_id, output_mode, reasoning_effort, max_tokens)
        probes.append(row)
        if row["status"] in STOP_KINDS:
            break
    listing_keys = ("id", "context_length", "supported_parameters", "json_output", "structured_outputs", "stability")
    listing = [{key: model.get(key) for key in listing_keys} for model in models]
    tested_at = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    return {"tested_at": tested_at, "base_url": client.base_url, "models": listing, "probes": probes}
