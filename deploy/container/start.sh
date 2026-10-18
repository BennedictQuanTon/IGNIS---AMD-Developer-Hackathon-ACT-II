#!/bin/sh
# Start the workflow API on loopback, wait until it is healthy, then run Caddy on :7860.
# IGNIS_MODE=replay (default) serves the committed recordings and needs no key.
# IGNIS_MODE=live uses MODEL_* / EXPLANATION_* secrets and spends the shared AMD quota.
set -eu

MODE="${IGNIS_MODE:-replay}"
DATA="${IGNIS_DATA:-/tmp/ignis}"
mkdir -p "$DATA"

case "$MODE" in
  replay)
    python -u scripts/serve_hosted.py --replay-dir docs/benchmarks/replay \
      --db "$DATA/state.sqlite3" --data "$DATA" &
    ;;
  live)
    if [ -z "${MODEL_API_KEY:-}" ]; then
      echo "IGNIS_MODE=live needs the MODEL_API_KEY secret" >&2
      exit 1
    fi
    python -u scripts/serve_hosted.py --db "$DATA/state.sqlite3" --data "$DATA" \
      --record-dir "$DATA/recorded" &
    ;;
  *)
    echo "IGNIS_MODE must be replay or live, got: $MODE" >&2
    exit 1
    ;;
esac
BACKEND_PID=$!

i=0
until python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=2)" 2>/dev/null; do
  i=$((i + 1))
  if [ "$i" -ge 60 ] || ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "workflow API did not become healthy" >&2
    exit 1
  fi
  sleep 1
done
echo "workflow API ready ($MODE); starting Caddy on :${PORT:-7860}"

exec caddy run --config deploy/container/Caddyfile --adapter caddyfile
