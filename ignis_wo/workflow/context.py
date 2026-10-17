"""Reviewed applicability filtering and deterministic lexical retrieval."""
import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ignis_wo.hashing import content_hash

ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = ROOT / "docs" / "synthetic-pump" / "corpus.json"
GRAPH_PATH = ROOT / "docs" / "synthetic-pump" / "applicability.json"
GRAPH = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
APPROVED_STATUSES = {"simulated_approved", "approved"}
PROVENANCE_KEYS = ("source_sha256", "artifact_id", "reader")
STOPWORDS = {"the", "and", "with", "for", "from", "this", "that", "was", "were", "has", "have", "into", "record", "observed"}


def fixture_sources() -> tuple[dict, dict]:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8")), GRAPH


def passage_for(item: dict, score: int, path: dict) -> dict:
    """Fixture items are whole documents; reviewed snapshot items are chunks with their own passage_id."""
    passage = {"passage_id": item.get("passage_id", item["document_id"]), "document_id": item["document_id"], "version": item["version"], "source_id": item["source_id"], "location": item["location"], "text": item["text"], "score": score, "applicability_path": path}
    passage.update({key: item[key] for key in PROVENANCE_KEYS if key in item})
    return passage


def retrieve(asset_id: str | None, component: str | None, query: str, facts: list[dict], snapshot_id: str, sources: tuple[dict, dict] | None = None):
    """`sources` is an injected (corpus, graph) snapshot; None uses the synthetic fixture corpus explicitly."""
    corpus, graph = sources if sources is not None else fixture_sources()
    corpus_mode = "synthetic_fixture" if sources is None else "reviewed_snapshot"
    if not asset_id or not component or asset_id not in graph["assets"]:
        return {"status": "insufficient_applicability", "reason": "asset and component identity must match the reviewed applicability map", "trace": {"eligible_ids": [], "excluded": [], "paths": []}, "pack": None}
    asset = graph["assets"][asset_id]
    allowed = asset["components"].get(component)
    if allowed is None:
        return {"status": "insufficient_applicability", "reason": "component is not mapped for this asset", "trace": {"eligible_ids": [], "excluded": [], "paths": []}, "pack": None}
    selected, excluded, paths = [], [], []
    for item in corpus["documents"]:
        path_ok = item["document_id"] in allowed and item["asset_model"] == asset["model"] and item["component"] == component
        eligible = path_ok and item["status"] in APPROVED_STATUSES and bool(item["reviewer"])
        path = {"asset_id": asset_id, "component": component, "document_id": item["document_id"], "graph_version": graph["graph_version"]}
        if eligible:
            selected.append(item)
            if path not in paths:
                paths.append(path)
        else:
            excluded.append({"document_id": item["document_id"], "reason": "not on reviewed path / wrong model or component" if not path_ok else item["status"]})
    tokens = lambda text: [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]
    q = set(tokens(query))
    ranking = []
    for item in selected:
        words = tokens(item["text"])
        overlap = sum(words.count(word) for word in q)
        if overlap:
            ranking.append((overlap, item.get("passage_id", item["document_id"]), item))
    ranking.sort(key=lambda row: (-row[0], row[1]))
    passages = [passage_for(row[2], row[0], next(p for p in paths if p["document_id"] == row[2]["document_id"])) for row in ranking[:3]]
    pack_data = {"pack_version": "evidence-pack-v1", "snapshot_id": snapshot_id, "asset_id": asset_id, "component": component, "query": query, "facts": [f for f in facts if f.get("scope", {}).get("component") == component], "passages": passages, "graph_version": graph["graph_version"], "corpus_version": corpus["corpus_version"], "synthetic": corpus.get("synthetic", True)}
    # No benchmark target or answer labels enter this inference pack.
    pack = {"pack_id": "EP-" + content_hash(pack_data), **pack_data}
    return {"status": "ready" if passages else "context_unavailable", "reason": None if passages else "no eligible passage matched the query", "corpus_mode": corpus_mode, "trace": {"eligible_ids": sorted({i["document_id"] for i in selected}), "excluded": excluded, "ranks": [{"passage_id": p["passage_id"], "rank": i + 1, "score": p["score"]} for i, p in enumerate(passages)], "paths": paths}, "pack": pack}


class DraftBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    fact_id: str
    value: float
    unit: str
    scope: dict[str, str]
    snapshot_id: str


class DraftClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    text: str
    citations: list[str] = Field(min_length=1)
    fact_bindings: list[DraftBinding] = []


class ExplanationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    pack_id: str
    hypotheses: list[DraftClaim]
    alternatives: list[DraftClaim]
    uncertainty: str
    inspection: DraftClaim | None = None
    abstain: bool


NUMBER_WORDS = re.compile(r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|dozen)\b", re.I)


def validate_draft(pack: dict, draft: dict):
    errors = []
    try:
        draft = ExplanationDraft.model_validate(draft).model_dump(mode="json")
    except ValidationError as error:
        return [f"draft schema invalid: {error.errors()[0]['msg']}"]
    if draft["pack_id"] != pack.get("pack_id"):
        errors.append("pack_id does not match frozen evidence pack")
    if not draft["abstain"] and not draft["hypotheses"]:
        errors.append("non-abstaining draft requires at least one hypothesis")
    fact_ids = {f["fact_id"] for f in pack["facts"]}
    fact_by_id = {f["fact_id"]: f for f in pack["facts"]}
    passage_ids = {p["passage_id"] for p in pack["passages"]}
    prose = [draft["uncertainty"]]
    claims = draft["hypotheses"] + draft["alternatives"] + ([draft["inspection"]] if draft["inspection"] else [])
    for claim in claims:
        citations = claim["citations"]
        for citation in citations:
            if citation not in fact_ids and citation not in passage_ids:
                errors.append(f"citation {citation!r} is not in the pack")
        prose.append(claim["text"])
        for binding in claim["fact_bindings"]:
            fact = fact_by_id.get(binding["fact_id"])
            if fact is None or fact["value"] != binding["value"] or fact["unit"] != binding["unit"] or fact["scope"] != binding["scope"] or fact["snapshot_id"] != binding["snapshot_id"] or binding["snapshot_id"] != pack["snapshot_id"]:
                errors.append(f"fact binding {binding['fact_id']!r} does not exactly match a scoped pack fact")
            if binding["fact_id"] not in citations:
                errors.append(f"fact binding {binding['fact_id']!r} must also be cited")
    for text in prose:
        if re.search(r"\d", text) or NUMBER_WORDS.search(text):
            errors.append("numbers in prose must be rendered from typed fact slots")
        if re.search(r"\b(replace|repair|shut down|dispatch|must|should immediately)\b", text, re.I):
            errors.append("authoritative maintenance actions are prohibited")
    return sorted(set(errors))
