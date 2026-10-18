# Free-tier demo deployment

A public, replay-only demo for judging: one Render free web service runs the workflow API and the review workspace from a Docker image, and the Vercel landing page forwards `/api` to it. No AMD key is stored on Render, so visitors cannot spend the shared quota. Live inference is demonstrated locally (see [LOCAL_RUN.md](../docs/LOCAL_RUN.md)).

```text
Browser ─ Vercel (landing + workspace, frontend/) ── /api/* ──┐
Browser ─ https://<service>.onrender.com ─────────────────────┤
                                                               ▼
                 Render web service :$PORT ─ Caddy ─ strips /api ─▶ workflow API on 127.0.0.1:8765 (replay)
```

| File | Purpose |
| --- | --- |
| [`render.yaml`](../render.yaml) | Blueprint: Docker runtime, `plan: free`, health check `/api/health`, `IGNIS_MODE=replay` |
| `container/Dockerfile` | Builds the frontend, installs `requirements.txt`, adds Caddy, fetches MaintIE (for optional live mode) |
| `container/Caddyfile` | Listens on `$PORT`, serves `frontend/dist` and proxies `/api/*` to the loopback API with a 300 s timeout |
| `container/start.sh` | Starts the API in `IGNIS_MODE=replay` (default) or `live`, waits for `/health`, then runs Caddy |
| [`.dockerignore`](../.dockerignore) | Keeps `.env`, `outputs/`, `data/` and `node_modules` out of the image |

## Publish

1. Sign in to Render with GitHub and give it access to this repository.
2. **New → Blueprint**, select the repository and `main`. Render reads `render.yaml` and creates the free `ignis` web service. If a card is requested, check the plan shows **Free**.
3. Wait for the build, then check `https://<service>.onrender.com/api/health` reports `hosted_replay`.
4. Point the Vercel rewrite in `frontend/vercel.json` at `https://<service>.onrender.com/api/:path*` and redeploy. The current service is `https://ignis-r64l.onrender.com`.

## Behaviour and limits

- **Replay only.** Changing inputs, decisions, criticality or the query can miss the recordings; the workspace then shows an unavailable/invalid draft rather than a live substitute.
- **Sleeps after 15 minutes idle.** The first request after that takes about a minute while the service starts. Open the URL shortly before a judging session.
- **Temporary storage.** Runs, decisions and PDFs live under `/tmp/ignis` and reset on every restart, redeploy or sleep.
- **Small instance.** Free instances have 512 MB RAM and a fraction of a CPU; replay and PDF rendering fit, live OCR is not intended here.
- **No authentication.** The API has none; the replay-only, key-free setup is what makes public access acceptable. Do not set `IGNIS_MODE=live` with `MODEL_*` secrets on a public service.
- **Long requests.** Vercel waits up to 120 s for the first byte; replay responses return immediately.

## Local rehearsal

With Docker running:

```sh
docker build -f deploy/container/Dockerfile -t ignis-demo .
docker run --rm -e PORT=10000 -p 10000:10000 ignis-demo
```

Without Docker (needs `caddy` 2.8 on `PATH`):

```sh
cd frontend && VITE_API_BASE=/api npm run build && cd ..
PORT=10000 IGNIS_WEB_ROOT="$PWD/frontend/dist" IGNIS_DATA="$PWD/outputs/demo-sim" sh deploy/container/start.sh
uv run --no-project --with-requirements requirements-dev.txt python scripts/check_local_replay.py \
  --base-url http://127.0.0.1:10000/api --out outputs/demo-sim-check
```

Fallback if Render is unavailable: run the same replay stack locally and expose port 10000 with a Cloudflare quick tunnel (`cloudflared tunnel --url http://127.0.0.1:10000`), then point the Vercel rewrite at the tunnel URL.
