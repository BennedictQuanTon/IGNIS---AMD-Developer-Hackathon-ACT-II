# Local workflow API

The service is a local, single-operator demonstration backend. It binds only to `127.0.0.1`; this does not provide production authentication or multi-user controls. SQLite stores run state and history. Source uploads accept CSV, TSV, JSON, JSONL, and XLSX (`content_base64` for binary XLSX). The default extraction and explanation providers are unavailable. Fixture extraction and manually supplied cited drafts are explicit alternatives; hosted inference is not configured.

## Start and seed (Windows PowerShell, repository root)

```powershell
uv run --no-project --with-requirements requirements-dev.txt python scripts/seed_demo.py --reset
uv run --no-project --with-requirements requirements-dev.txt python -m ignis_wo serve --db outputs/demo-backend/state.sqlite3 --data outputs/demo-backend --fixture-items tests/fixtures/maintie_sample.json
```

The seed command creates a synthetic pump run, fixture-based extraction, simulated decision/signoff and an issued PDF under `outputs/demo-backend`. Its signoff is explicitly simulated, not a real human review. `--reset` removes only the selected child directory of `outputs`; omit it to preserve prior local state. The API serves at `http://127.0.0.1:8765`; `GET /health` confirms readiness.

## Revision and errors

Every mutation requires `expected_revision` from the latest run response. A successful mutation increments `revision`; stale revisions return HTTP 409 `revision_conflict` before provider calls or published-file changes. Invalid requests return 422 `request_failed`; missing fields return 400 `missing_field`; unknown run/report returns 404. Actual upload parser and PDF renderer failures are persisted as events, increment the run revision, set the owning stage to `failed`, append a stage error, and return HTTP 422 `stage_failed` with `stage`, `current_revision`, and the updated `run`. Retry using that returned revision. A failed report render clears the active `latest_report` pointer; previously issued reports remain in immutable report history and downloadable. Ordinary validation failures and stale conflicts do not create stage-failure events. Responses retain explicit `stage_status` and `stage_errors`; unavailable providers do not fabricate progress.

## Provider adapter interfaces

Adapters are injected by the local Python host when constructing `Workflow`; no HTTP route accepts arbitrary provider code or credentials. `extraction_provider(records: list[CanonicalRecord]) -> list[ExtractionSuggestion]` receives canonical source rows and must return typed extraction suggestions. `explanation_provider(pack: dict) -> dict` receives the immutable evidence pack and returns the typed cited-draft contract described below. Explanation adapters may expose string attributes `model_id`, `prompt_id`, and `explanation_mode`; these are persisted as provenance. Extraction metadata remains separate from explanation metadata. Adapter exceptions are recorded at their stage. `scripts/serve_hosted.py` injects hosted AMD providers: extraction uses the frozen configuration in `ignis_wo/hosted/extraction_config.json` (its few-shot examples need `scripts/fetch_maintie.py`), and explanation retries once without `max_tokens` when a model rejects the 4096-token budget. Both roles share one request pacer per process.

## Reviewed document corpus

`Workflow(..., corpus_sources=(corpus, graph))` retrieves from a reviewed corpus snapshot. Without it, retrieval uses the synthetic fixture corpus, and `context.corpus_mode` reports `synthetic_fixture` or `reviewed_snapshot`. Eligibility is still filtered in code by reviewed status, asset model and component before the top three passages are ranked. Steps:

1. Read a document into unreviewed chunks: `python scripts/ingest_document.py manual.pdf --document-id MAN-1 --revision 1 --reader native`. Use `--reader mineru` for scans or images, which needs `DOCUMENT_OCR_MODEL`.
2. Approve the chunks for one asset model and component: `python scripts/review_document.py approve <artifact dir> --reviewer ... --reason ... --asset-model PX-100 --component seal`. Corrections are stored beside the raw text, which is never rewritten. Partial artifacts are refused.
3. Publish an immutable snapshot: `python scripts/review_document.py publish <artifact dirs> --asset PUMP-SYN-01=PX-100 --out outputs/corpus/pump-v1.json`.
4. Serve it: `python scripts/serve_hosted.py --corpus outputs/corpus/pump-v1.json`.

Reports record the extraction model that produced the suggestions (`extraction_identity`: model id, version and whether it is the scored configuration). Under context review they also list each evidence passage with its document version, page and chunk, source file hash and reader. Rebuilding context gives a new evidence pack and clears the draft and signoff. Issued PDFs stay in history.

## Routes

| Method and path | Purpose |
| --- | --- |
| `POST /runs` | Create run: `name`, `operator`, `synthetic`, `adapter_mode` (`unavailable`, `fixture`, `injected`) |
| `GET /runs`, `GET /runs/{id}` | List and inspect persistent runs |
| `POST /runs/{id}/upload` | Upload `{expected_revision, filename, csv_text}` or `{expected_revision, filename, content_base64}` |
| `GET /runs/{id}/preview` | Preview rows and proposed mapping before confirmation |
| `POST /runs/{id}/mapping/confirm` | Confirm `{expected_revision, mapping, reason}` explicitly |
| `POST /runs/{id}/extraction/start` | Start configured extraction; unavailable is recorded honestly |
| `POST /runs/{id}/records/{record_id}` | Review one record with `status` accepted/corrected/rejected, `reason`, optional correction/reviewer; pending and rejected records do not enter analysis |
| `POST /runs/{id}/analyze` | Compute snapshot, typed facts and deterministic alerts; optional supervisor `criticalities` |
| `POST /runs/{id}/context` | Retrieve scoped evidence using `{expected_revision, asset_id, component, query}` |
| `POST /runs/{id}/context/generate` | Invoke only an explicitly injected explanation adapter |
| `POST /runs/{id}/context/draft` | Validate manually supplied typed/cited draft against current immutable evidence pack |
| `POST /runs/{id}/expert-review` | Record accepted/corrected/rejected/inconclusive or explicit `facts_only_approved` review |
| `POST /runs/{id}/reports/issue` | Issue immutable PDF after current snapshot/pack/draft signoff |
| `GET /runs/{id}/facts`, `/alerts`, `/context`, `/reports`, `/history` | Read current outputs and append-only events/report history |
| `GET /runs/{id}/report/{report_id}` | Download an issued report, including older issued versions |

The `demo_auto_review` boolean is only accepted for a synthetic run in fixture mode and leaves a visible automatic-demo attribution. No operational/maintenance dispatch or prediction endpoint exists.

## Request examples

Create a run:

```json
{"name":"pump demo","operator":"local-reviewer","synthetic":true,"adapter_mode":"fixture"}
```

Upload and previewable mapping:

```json
{"expected_revision":0,"filename":"pump.csv","csv_text":"WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h)\nWO-1,PUMP-SYN-01,2025-01-01,pump seal leaking,2\n"}
```

Confirm mapping using the returned proposal, then call extraction and make a decision for each record. A valid draft claim uses `{text,citations,fact_bindings}`; fact bindings must match value, unit, asset/component scope and snapshot. The draft itself includes `pack_id`, `hypotheses`, `alternatives`, `uncertainty`, typed `inspection`, and `abstain`. Numeric prose is rejected so report numbers remain sourced from facts. An expert decision is tied to the exact current snapshot, pack and draft hash.

Typical run response fields are `run_id`, `revision`, `status`, `stage_status`, and current `snapshot`, `facts`, `alerts`, `context`, and report references. State is safe to reload after process restart; old issued reports remain downloadable after upstream corrections while the active run loses stale approvals and outputs.
