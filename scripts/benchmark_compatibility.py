"""#23 Stage 0: a cheap compatibility screen before any benchmark job.

Run with: uv run --env-file .env --no-project --with-requirements requirements-dev.txt python scripts/benchmark_compatibility.py
Lists the catalogue, reads one synthetic page with the OCR model, and sends one minimal JSON request
to each processing model with an explicit 4096-token budget and the opt-in fallback, so a null-limit
rejection and the fallback are both recorded. Failures are kept, never dropped.
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.evaluation.jobs import JobBudget  # noqa: E402
from ignis_wo.evaluation.reader_benchmark import FAMILIES, family_files  # noqa: E402
from ignis_wo.hashing import sha256_bytes  # noqa: E402
from ignis_wo.hosted.ocr import OcrClient  # noqa: E402
from ignis_wo.hosted.pacing import RequestPacer  # noqa: E402
from ignis_wo.hosted.providers import client_from_environment  # noqa: E402
from ignis_wo.hosted.transport import ProviderError  # noqa: E402

MESSAGES = [{"role": "system", "content": "Return only a JSON object."},
            {"role": "user", "content": 'Return {"status": "ok"}.'}]


def probe(name: str, call) -> dict:
    try:
        return {"probe": name, "outcome": "ok", **call()}
    except ProviderError as error:
        return {"probe": name, "outcome": error.kind, "http_status": error.status, "message": str(error)[:300]}


def chat_probe(client, model: str) -> dict:
    result = client.complete(model, MESSAGES, reasoning_effort="low", max_tokens=4096, budget_fallback=True)
    return {"finish_reason": result.finish_reason, "usage": result.usage, "latency_seconds": result.latency_seconds,
            "request_parameters": result.request_parameters, "content": result.content[:200]}


def ocr_probe(client, model: str) -> dict:
    _, data, _ = family_files("F3-clean-scan", FAMILIES["F3-clean-scan"])[0]
    result = OcrClient(client.gateway, model).read(data, "image/png", [0], sha256_bytes(data))
    return {"pages": len(result.pages), "usage": result.usage, "latency_seconds": result.latency_seconds,
            "characters": len(result.pages[0]["markdown"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=["DeepSeek-V4-Flash", "Qwen3.8-27B"])
    parser.add_argument("--ocr-model", default=os.environ.get("DOCUMENT_OCR_MODEL"))
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "benchmarks" / "23" / "stage0")
    arguments = parser.parse_args()
    job = JobBudget("stage0", 12, 900)
    client = client_from_environment(pacer=RequestPacer(20, 1, 0.25))
    client.gateway.budget = job
    catalogue = probe("catalogue", lambda: {"models": sorted(model.get("id") for model in client.list_models())})
    probes = [catalogue]
    if arguments.ocr_model:
        probes.append(probe(f"ocr:{arguments.ocr_model}", lambda: ocr_probe(client, arguments.ocr_model)))
    for model in arguments.models:
        probes.append(probe(f"chat:{model}", lambda model=model: chat_probe(client, model)))
    arguments.out.mkdir(parents=True, exist_ok=True)
    summary = {"probes": probes, "job": job.write(arguments.out / "job")}
    (arguments.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
