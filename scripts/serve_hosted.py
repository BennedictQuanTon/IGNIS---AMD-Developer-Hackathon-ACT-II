"""Start the local workflow API with hosted AMD extraction and explanation providers.

Run with: uv run --env-file .env --no-project --with-requirements requirements-dev.txt python scripts/serve_hosted.py
Create runs with adapter_mode "injected" to use hosted extraction. Every live response is recorded
under --record-dir so it can be replayed without spending the shared quota. Hosted extraction uses the
frozen few-shot configuration, so run scripts/fetch_maintie.py once before setting MODEL_NAME.
Pass --corpus with a snapshot from scripts/review_document.py to retrieve reviewed documents; without it
the synthetic fixture corpus is used, and the startup line says which.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.documents.corpus import load_corpus_snapshot  # noqa: E402
from ignis_wo.hosted.providers import providers_from_environment, replay_providers  # noqa: E402
from ignis_wo.workflow.api import serve  # noqa: E402
from ignis_wo.workflow.service import Workflow  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "outputs" / "hosted-backend" / "ignis.sqlite3")
    parser.add_argument("--data", type=Path, default=ROOT / "outputs" / "hosted-backend")
    parser.add_argument("--record-dir", type=Path, default=ROOT / "outputs" / "hosted-backend" / "recorded")
    parser.add_argument("--max-records", type=int, default=25, help="records per live extraction run")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--corpus", type=Path, help="reviewed corpus snapshot (default: synthetic fixture corpus)")
    parser.add_argument("--replay-dir", type=Path, help="serve recorded providers only (e.g. docs/benchmarks/replay); no key needed")
    arguments = parser.parse_args()

    if arguments.replay_dir:
        extraction_provider, explanation_provider = replay_providers(arguments.replay_dir, arguments.max_records)
    else:
        extraction_provider, explanation_provider = providers_from_environment(
            record_directory=arguments.record_dir, max_records=arguments.max_records)
    print(f"providers: {'replay from ' + str(arguments.replay_dir) if arguments.replay_dir else 'hosted live'}", flush=True)
    if extraction_provider is None and explanation_provider is None:
        raise SystemExit("set MODEL_NAME and/or EXPLANATION_MODEL_NAME in .env to enable hosted providers")
    corpus_sources = load_corpus_snapshot(arguments.corpus) if arguments.corpus else None
    corpus_line = f"reviewed corpus {corpus_sources[0]['corpus_version']}" if corpus_sources else "synthetic fixture corpus"
    print(f"evidence: {corpus_line}", flush=True)
    arguments.data.mkdir(parents=True, exist_ok=True)
    workflow = Workflow(arguments.db, arguments.data, extraction_provider=extraction_provider,
                        explanation_provider=explanation_provider, corpus_sources=corpus_sources)
    serve(workflow, arguments.host, arguments.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
