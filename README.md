# IGNIS

IGNIS is a maintenance-evidence desk built for **AMD Developer Hackathon: ACT III**, **Track 1: Intelligent Industry**. A reviewer uploads a historical work-order export, confirms the column mapping, reviews model-suggested component / fault / action spans, and then receives code-computed facts, deterministic priority alerts, a small pack of applicable manual passages, a cited explanation draft, and — after an explicit sign-off — a PDF whose numbers come from those facts.

The running demonstration uses a **synthetic pump** (`PUMP-SYN-01`) and a **recorded replay** of AMD-hosted model calls. It does not connect to a factory, predict failures, or authorize repairs. Broader sensor, dispatch and fine-tuning designs are written proposals; they are listed separately below.

## The competition

| | |
|---|---|
| Event | [AMD Developer Hackathon: ACT III](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii) on lablab.ai |
| Track | Track 1 · Intelligent Industry — help factories see what matters and what to inspect next |
| Window | Online build, 12–18 October 2026. The reviewed event page lists final submission at 18 October 2026, 15:00 UTC (22:00 Bangkok). Recheck the [live event page](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/live) before relying on dates. |
| Prize pool | $17,000+ across the event |
| Tracks | 5 (4 themed tracks plus Evolus) |
| Judging | Application of Technology, Presentation, Business Value, Originality |
| AMD requirement | AMD technology has to be part of the working product. IGNIS calls the event's AMD API (Radeon Cloud chat completions) for extraction and explanation. The default public demo replays those calls and stores no API key. |

Team name: **Team Develarper**. Repository: [khanhtuongnakitomo/IGNIS](https://github.com/khanhtuongnakitomo/IGNIS).

## The product

IGNIS separates three jobs that a chat window usually mixes together.

1. **Models propose.** A hosted model suggests entities on each work-order row, and later drafts a cited explanation from a frozen evidence pack.
2. **Code computes.** Counts, severity, recurrence and priority come from versioned rules over the approved snapshot. Report numbers are rendered from typed facts. A claim that cites nothing in the pack, or that writes a quantity in prose, is rejected before a PDF can be issued.
3. **People approve.** A named reviewer accepts, corrects or rejects each record. A separate expert decision accepts, corrects, rejects or marks the finding inconclusive. Rejected and inconclusive findings cannot issue a report. Sign-off in the seeded demo is labelled simulated.

The first asset in the demo is a motor-driven pump with seal-leakage work orders. Six synthetic rows are committed as [`docs/benchmarks/replay/demo_input.csv`](docs/benchmarks/replay/demo_input.csv).

### What one demo run produces

A guided or manual run persists a single SQLite history. After the recorded scenario finishes, the saved run contains:

| Output | What it is |
|---|---|
| Source snapshot | The uploaded file, its SHA-256, the confirmed column mapping, and one stable id per row |
| Extraction | Component, fault and action suggestions anchored to the source text. In replay mode these are the recorded DeepSeek-V4-Flash-Vision-Exp labels, not a new model call |
| Review decisions | Accept, correct or reject per record, with reviewer and reason. Pending and rejected rows stay out of the approved snapshot |
| Facts | Typed counts and measures over the approved rows, each fact pointing at its source record ids |
| Alerts | A historical priority from severity × recurrence × a supervisor criticality multiplier. This is an ordering for review, not a failure probability |
| Evidence pack | Up to three passages that passed an applicability filter (reviewed status, asset model, component). Wrong-model and superseded sources are excluded before ranking |
| Cited draft | Hypotheses, alternatives, uncertainty and a suggested inspection step, each citation bound to a passage or fact in that pack. Status on the recorded run is `pending_expert_review` |
| Expert decision | Accept, correct, reject, inconclusive, or facts-only when context is unavailable. The demo sign-off is attributed to `SYNTHETIC DEMO SIGNOFF SIMULATOR` |
| PDF | Issued only after an accepted or corrected finding. Older PDFs stay downloadable after a later correction; the active approval does not |

Replay is exact. Changing the operator, mapping, record reviewer, criticality or evidence query changes the snapshot or pack id. A miss is shown as an unavailable or invalid draft. The app does not silently call the live API in its place.

## The interface

The browser app is a React 19 / TypeScript / Vite site. Visual language is a dark evidence desk: near-black surfaces, system fonts, one yellow accent (`#FFC400`), and status that is always a word as well as a colour. Landing copy and figures live in [`frontend/src/content/site.ts`](frontend/src/content/site.ts).

Hash routes, no server-side router:

| Route | Screen |
|---|---|
| `#/` | Landing page |
| `#/app` | Guided demo of the recorded six-row scenario |
| `#/app/manual` | Manual workspace on the same API |

### Landing page

One scrolling page, in this order:

1. **Nav** — wordmark, anchors, GitHub. A demo button stays hidden until `demoUrl` is set.
2. **Hero** — “The evidence system for maintenance teams and AI”, plus a scaled illustrative workspace window. That window is a labelled synthetic illustration, not a screenshot of a live run.
3. **Challenge** — event facts and the four judging criteria.
4. **Problem** — three cited industry figures (reactive maintenance, work-order text quality, downtime cost). The page states these are problem context, not IGNIS savings.
5. **Product** — the seven-step flow with an `AI` / `CODE` / `HUMAN` owner on each step.
6. **Features** — the six cards below.
7. **Product frame** — reserved for a real capture. `productScreenshot` is still empty, so the frame stays a placeholder.
8. **Stack, delivered metrics, comparison, team, sources, close.**
9. A **2:14 demo film** is wired at `frontend/public/media/ignis-demo.mp4` when that asset is served with the site.

### Guided demo (`#/app`)

The demo drives the workflow API with the recorded scenario. **Continuous** mode plays each stage. **Manual** mode stops on each form; replay-bound fields accept only the recorded value, with a “Fill recorded values” shortcut. The rail is Source → Mapping → Record review → Facts → Evidence → Expert signoff → Report.

The run stops at expert sign-off. Accept and correct then issue the PDF. Reject and inconclusive block the report and leave facts and evidence in place. The header shows **Replay** or **Live**, and a flask mark when the run is synthetic.

### Manual workspace (`#/app/manual`)

A left rail lists saved runs and six stages with backend status: **Source, Mapping, Review, Facts, Evidence, Report**. The main column is the form for that stage. An evidence inspector opens any fact, source row or passage id. An audit list shows the append-only revision history. Refresh reloads SQLite state after a restart.

When the server is in live mode, model calls stay off until the operator checks **Enable live calls (shared quota)**. The browser never sees the AMD key.

## Features in the running app

| Feature | Behaviour today |
|---|---|
| Export intake | CSV, TSV, JSON, JSONL and XLSX. The file hash is stored. A person confirms the proposed column mapping before any row is canonical |
| Span-level extraction | Suggestions name component, fault and action against the source text. The demo replays a frozen few-shot AMD call. A live call uses the same frozen config when a key is present |
| Human review gate | Accept, correct or reject each record. Nothing enters the snapshot until that decision is saved |
| Code-computed priority | Versioned rules in `ignis_wo/config/`. Alerts are historical triage, not a predicted failure |
| Scoped evidence | Applicability filtering, then the top passages for the chosen asset, component and query. The default corpus is a synthetic fixture; a reviewed snapshot can be published and served instead |
| Checked report | Draft validation rejects unbound claims and digits written as prose, so quantities stay on typed facts. The PDF is issued only after the current snapshot, pack and draft are signed |

Also implemented, and easy to miss from the landing cards:

- Revision checks on every mutation (`expected_revision`, HTTP 409 on a stale client).
- Persistent runs, decisions and issued PDFs in SQLite.
- Honest provider state: unavailable, fixture, replay or live. A missing model does not invent a draft.
- A facts-only approval path when retrieval or the draft is unavailable.
- Document reading for a separate corpus workflow: native `pypdf` for text PDFs, MinerU OCR for scans and images.

## Benchmarks and what the output means

Measurements were taken on **16–17 October 2026** against the event AMD API, one shared key, **20 requests per minute** and **$1 per day**. Each published job is a single small run. The API ignores `seed`, so a repeat can differ. Full tables, charts and the frozen inputs are in [docs/BENCHMARKS.md](docs/BENCHMARKS.md), [docs/benchmarks/results.json](docs/benchmarks/results.json) and [docs/benchmarks/manifest.json](docs/benchmarks/manifest.json).

These numbers are preliminary API measurements. They are not a GPU benchmark, a factory accuracy study, or a claim that a model was fine-tuned.

### Roles that were measured

| Role | Configuration that the demo uses | What was measured |
|---|---|---|
| Document reader | Native text extraction; MinerU2.5-Pro (`/ocr`) for scans and images | 12 synthetic pages. Text, tables and scans were nearly exact. Diagram labels were dropped (mean character error 0.617 on the held-out diagram family) |
| Work-order extraction | DeepSeek-V4-Flash-Vision-Exp, frozen few-shot, JSON object output | MaintIE **test** split, 108 records, scored once and not re-run: **105 / 108** valid outputs, exact entity F1 **0.46**, depth-2 F1 **0.59**, top-level label F1 **0.76**, relation F1 **0.43**, latency p50 / p95 **8.8 / 12.8 s**. Source: the scored block in [`ignis_wo/hosted/extraction_config.json`](ignis_wo/hosted/extraction_config.json) |
| Explanation | DeepSeek-V4-Flash, reasoning `low`, prompt **v3** | Two synthetic dev runs pooled: **21 / 24** final valid outputs, support-or-abstain matched the expected label on **16 / 23**, median model time about **10 s**. Qwen3.8-27B wrote cleaner drafts and was too slow for the demo (median over 100 s, timeouts at the 180 s client limit) |

A separate **dev** extraction timing check (MaintIE records 0–19, not the test split) produced 20 / 20 valid outputs at about **5.9** valid records per minute with concurrency 1 and **10.8** with concurrency 2. Exact entity F1 on that slice was 0.59 and 0.56. That check is a runtime sample. It does not replace the test-split score above.

### Why prompt v3 is the default

v2 and v3 were each run twice on the same 12 synthetic dev scenarios. v3 was valid more often (21/24 vs 14/24), abstained on every case that required abstention, and was about twice as fast. It also abstained on some cases whose frozen label expected support, and it cited an expected passage less often. The team kept that caution because a person still reviews the draft. v1 and v2 remain selectable with `EXPLANATION_PROMPT_VERSION`. Expected labels were drafted by Yoshio and were still pending Tuong's review when these runs were published. Semantic support is not an automatic score; a blind rating sheet is in [docs/benchmarks/rating/blind_sheet.csv](docs/benchmarks/rating/blind_sheet.csv).

### What a benchmark job writes

| Artifact | Contents |
|---|---|
| [`docs/benchmarks/results.json`](docs/benchmarks/results.json) | Aggregated validity, decision match, citation hits, latency and quota snapshots per job |
| [`docs/benchmarks/manifest.json`](docs/benchmarks/manifest.json) | Frozen inputs, models, prompt ids and scoring rules |
| `docs/benchmarks/*/summary.json` and `rows.jsonl` | Per-stage and per-prompt summaries |
| `docs/benchmarks/charts/*.svg` | Reader error, explanation quality and throughput charts |
| [`docs/benchmarks/replay/`](docs/benchmarks/replay/summary.json) | One live synthetic-pump recording: extraction of the six demo rows, one v3 explanation that reached `pending_expert_review`, and the pilot OCR replies. Offline replay reproduced the same labels and the same draft |

Replaying that package needs no key and no network:

```bash
uv run --no-project --with-requirements requirements-dev.txt \
  python scripts/serve_hosted.py --replay-dir docs/benchmarks/replay
```

Upload `docs/benchmarks/replay/demo_input.csv` with adapter mode `injected`, or open the guided demo, which loads the same file from the API.

## Team

**Team Develarper**

| Name | Role | Owns |
|---|---|---|
| [Khanh Tuong Huynh](https://github.com/khanhtuongnakitomo) | Team lead · AI engineer | Backend pipeline, review data, alerts, retrieval, evidence-linked reports |
| [Long Quan Ton](https://github.com/BennedictQuanTon) | AI engineer · frontend | UI, workspace, demo film, end-to-end checks |
| [Yoshio Nomura](https://github.com/UniverseScripts) | AI engineer · LLMOps | AMD API integration, MaintIE prompts, quality and latency benchmarks |

Photos used on the landing page are `frontend/public/team/khanh-tuong-huynh.jpg`, `long-quan-ton.jpg` and `yoshio-nomura.jpg`.

## Designed, and not a running service

The documents below describe a larger system. Adopting that direction does not mean the pieces are implemented or measured.

- Hourly sensor monitoring, deviation alerts, and a case knowledge base that grows after expert confirmation.
- Historical playback and a simulated live stream of bearing temperature, vibration and motor current.
- Technician assignment, maintenance scheduling, and production-loss-aware dispatch.
- LoRA adapters for extraction and explanation, released only after a held-out evaluation.
- Thermal-image anomaly detection and failure prediction. Both need authorized labels and an asset- and time-aware evaluation that this repository does not contain.

Read [docs/PROPOSAL.md](docs/PROPOSAL.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/PROPOSED_SYSTEM_WORKFLOW.md](docs/PROPOSED_SYSTEM_WORKFLOW.md). The interactive diagrams under `artifacts/` walk through those proposals with synthetic flows.

## Run the recorded demo

The committed launcher is PowerShell and is documented for the Windows machine in [docs/LOCAL_RUN.md](docs/LOCAL_RUN.md):

```powershell
.\scripts\start_local.ps1
```

That starts replay mode on `127.0.0.1:8765` and the Vite app on `127.0.0.1:5173`.

- Landing: http://127.0.0.1:5173/
- Guided demo: http://127.0.0.1:5173/#/app
- Manual workspace: http://127.0.0.1:5173/#/app/manual
- Health: http://127.0.0.1:8765/health

On macOS or Linux, the same processes are:

```bash
mkdir -p outputs/hosted-backend
uv run --no-project --with-requirements requirements-dev.txt \
  python scripts/serve_hosted.py \
  --replay-dir docs/benchmarks/replay \
  --db outputs/hosted-backend/ignis.sqlite3 \
  --data outputs/hosted-backend

# second terminal, after npm ci inside frontend/
cd frontend
IGNIS_API_PROXY=http://127.0.0.1:8765 VITE_API_BASE=/api \
  npm run dev -- --host 127.0.0.1 --port 5173
```

`npm ci` in `frontend/` is required before the first frontend start. Node.js and `uv` are required. AMD keys stay in the Python process (`.env`, never the browser). Live mode is `scripts/serve_hosted.py` without `--replay-dir`, with `MODEL_NAME`, `EXPLANATION_MODEL_NAME`, and MaintIE fetched by `scripts/fetch_maintie.py`.

A replay-only container recipe is in [deploy/README.md](deploy/README.md). `frontend/vercel.json` forwards `/api` to `https://ignis-r64l.onrender.com`. That host is a free-tier, key-free, temporary-disk demo. This README does not re-check that the host is awake.

### Checks

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python scripts/check_repository.py
```

`python scripts/check_repository.py` validates Markdown link targets and YAML/JSON syntax. The unit tests cover workflow behaviour in this repository. Neither check is a live-provider evaluation or a production-readiness result. When a frontend lockfile is present, CI also typechecks and builds `frontend/`.

## Repository map

- [Local run and browser checks](docs/LOCAL_RUN.md)
- [Workflow API](docs/API_CONTRACT.md)
- [Benchmark report](docs/BENCHMARKS.md)
- [Proposal](docs/PROPOSAL.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Proposed three-loop workflow](docs/PROPOSED_SYSTEM_WORKFLOW.md)
- [Frontend](frontend/README.md)
- [Design system](docs/design/DESIGN.md)
- [Deployment recipe](docs/DEPLOYMENT.md)
- [Contributing](CONTRIBUTING.md)
- [Security and data handling](SECURITY.md)
- [Agent rules for this repo](AGENTS.md)
- [MIT license](LICENSE)
