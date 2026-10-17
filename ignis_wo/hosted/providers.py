"""Builds the hosted providers from environment variables.

MODEL_API_KEY           shared event key (secret, never logged)
MODEL_BASE_URL          defaults to the AMD Token Factory URL
MODEL_NAME              extraction model; extraction stays unavailable when unset
EXPLANATION_MODEL_NAME  explanation model; explanation stays unavailable when unset

Load them with `uv run --env-file .env ...`.
Extraction uses the frozen configuration in extraction_config.json, so it needs the MaintIE train
split from scripts/fetch_maintie.py. Explanation sends max_tokens=4096 and, when a model rejects that
budget, retries once without it; both roles share one pacer per process.
"""

import os
from pathlib import Path

from ignis_wo.extraction.adapters import LiveAdapter
from ignis_wo.extraction.suggest import suggest_all
from ignis_wo.hosted.explanation import HostedExplanationProvider
from ignis_wo.hosted.frozen import frozen_extraction_adapter, load_train_items
from ignis_wo.hosted.pacing import RequestPacer, shared_pacer
from ignis_wo.hosted.transport import DEFAULT_BASE_URL, ChatClient


def client_from_environment(environment=None, pacer: RequestPacer | None = None) -> ChatClient:
    environment = os.environ if environment is None else environment
    api_key = environment.get("MODEL_API_KEY")
    if not api_key:
        raise ValueError("MODEL_API_KEY is not set; add it to .env and run with `uv run --env-file .env`")
    base_url = environment.get("MODEL_BASE_URL") or DEFAULT_BASE_URL
    return ChatClient(base_url, api_key, pacer=pacer or shared_pacer())


def extraction_provider_for(adapter: LiveAdapter, max_records: int):
    def extraction_provider(records):
        if len(records) > max_records:
            raise ValueError(f"live extraction is capped at {max_records} records per run to protect the shared quota")
        return suggest_all(records, adapter)

    extraction_provider.model_id = adapter.model_id
    extraction_provider.model_version = adapter.model_version
    extraction_provider.scored_configuration = adapter.scored_configuration
    return extraction_provider


def providers_from_environment(environment=None, record_directory: Path | None = None, max_records: int = 25,
                               train_items: list[dict] | None = None, frozen_config: dict | None = None):
    """Returns (extraction_provider, explanation_provider); each is None when its model is not configured.
    MaintIE train items are loaded only when extraction is configured."""
    environment = os.environ if environment is None else environment
    extraction_model = environment.get("MODEL_NAME")
    explanation_model = environment.get("EXPLANATION_MODEL_NAME")
    if not extraction_model and not explanation_model:
        return None, None
    client = client_from_environment(environment)
    if record_directory is not None:
        record_directory.mkdir(parents=True, exist_ok=True)
    extraction_provider = explanation_provider = None
    if extraction_model:
        record_path = record_directory / "extraction-replay.jsonl" if record_directory else None
        items = train_items if train_items is not None else load_train_items()
        adapter = frozen_extraction_adapter(client, extraction_model, items, record_path, frozen_config)
        extraction_provider = extraction_provider_for(adapter, max_records)
    if explanation_model:
        record_path = record_directory / "explanation-replay.jsonl" if record_directory else None
        explanation_provider = HostedExplanationProvider(client, explanation_model, record_path=record_path,
                                                         budget_fallback=True)
    return extraction_provider, explanation_provider
