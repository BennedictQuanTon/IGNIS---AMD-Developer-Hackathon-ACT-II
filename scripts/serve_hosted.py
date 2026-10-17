"""Start the local workflow API with hosted AMD extraction and explanation providers.

Run with: uv run --env-file .env --no-project --with-requirements requirements-dev.txt python scripts/serve_hosted.py
Create runs with adapter_mode "injected" to use hosted extraction. Every live response is recorded
under --record-dir so it can be replayed without spending the shared quota. Hosted extraction uses the
frozen few-shot configuration, so run scripts/fetch_maintie.py once before setting MODEL_NAME.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.hosted.providers import providers_from_environment  # noqa: E402
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
    arguments = parser.parse_args()

    extraction_provider, explanation_provider = providers_from_environment(
        record_directory=arguments.record_dir, max_records=arguments.max_records)
    if extraction_provider is None and explanation_provider is None:
        raise SystemExit("set MODEL_NAME and/or EXPLANATION_MODEL_NAME in .env to enable hosted providers")
    arguments.data.mkdir(parents=True, exist_ok=True)
    workflow = Workflow(arguments.db, arguments.data, extraction_provider=extraction_provider,
                        explanation_provider=explanation_provider)
    serve(workflow, arguments.host, arguments.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
