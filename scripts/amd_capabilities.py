"""Stage A capability smoke test: lists the AMD chat models and sends one tiny request per model and mode.

Run with: uv run --env-file .env --no-project --with-requirements requirements-dev.txt python scripts/amd_capabilities.py
Each probe is one billed request; --max-requests caps the total.
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ignis_wo.hosted.capabilities import capability_matrix  # noqa: E402
from ignis_wo.hosted.pacing import RequestPacer  # noqa: E402
from ignis_wo.hosted.providers import client_from_environment  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-requests", type=int, default=20)
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--requests-per-minute", type=float, default=10)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "capabilities")
    arguments = parser.parse_args()

    client = client_from_environment(pacer=RequestPacer(arguments.requests_per_minute, 1))
    matrix = capability_matrix(client, arguments.max_requests, arguments.reasoning_effort)
    arguments.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    path = arguments.out / f"capabilities-{stamp}.json"
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for row in matrix["probes"]:
        print(f"{row['model']:<32} {row['output_mode']:<12} {row['status']:<20} {row.get('latency_seconds', '')}")
    print(f"capability matrix: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
