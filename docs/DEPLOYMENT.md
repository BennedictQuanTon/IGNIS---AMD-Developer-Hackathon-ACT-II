# Deployment preparation

There is no deployable application in this repository yet. This document is a target checklist, not evidence of a configured cloud account, GPU quota, running service, or cost estimate.

## Candidate topology

- Browser client talks to an authenticated application API over HTTPS.
- API, ingestion, deterministic analytics, review state, and report generation run in an application service.
- A private inference endpoint runs the selected open model on a confirmed AMD ROCm-capable host when available.
- A persistent database and protected object storage are selected before real maintenance exports are accepted.

The October 13 scope revision adds a proposed seeded sensor simulator with historical and simulated-live modes, timestamped observation storage, windowed condition rules, a versioned logical knowledge graph, and graph-constrained document/history retrieval. These can start in the same small demo application process; dedicated time-series and graph services are alternatives to evaluate rather than configured infrastructure. No factory endpoint, sensor hardware, broker, simulator or graph service exists yet. See [the revised architecture](ARCHITECTURE.md#sensor-informed-rag-and-knowledge-graph-revision---october-13-2026).

The combined topology also includes checkpointed log readers and a watched/polled CSV/XLSX source location. Route telemetry, events and maintenance records separately, process only stable source versions, incrementally refresh graph/index revisions, and expose source freshness/index lag. Keep review/approval and issued-report evidence immutable across subsequent imports. The first demo uses simulated logs and local exports; no persistent reader, polling job or factory connector has been started by these design edits.

A demo may use one application process and SQLite if concurrency and persistence limits are clearly stated. Keep provider keys and database credentials server-side. Do not expose the inference endpoint directly to an unauthenticated browser.

## Readiness gates

The confirmed hourly loop requires a durable application scheduler, completed-hour/baseline comparison jobs, persisted alert cases, an authenticated expert-review path and an idempotent case/graph/index publisher. Select the scheduler/worker technology before implementation; this is not a Codex chat automation. Verify hour/timezone alignment, catch-up/checkpoint behavior, prior-only comparable baselines, inadequate-data notices and duplicate-alert handling. A model outage must not suppress deterministic deviation notices. Knowledge publication must require an accepted attributed review and keep graph/index versions consistent; baseline/rule updates need their own approval. No hourly scheduler, external alert channel, expert service or knowledge-publish job is currently deployed.

1. Reproduce environment setup from a clean checkout and lock runtime/dependency versions.
2. Confirm selected ROCm image, driver/runtime, model license, model revision, adapter behavior, structured-output support, memory use, and cold/warm latency on the actual host.
3. Exercise ingestion, review, deterministic snapshot, claim validation, PDF rendering, restart recovery, and per-record retry behavior with synthetic fixtures.
4. Choose identity, role permissions, retention/deletion, backup, logging, and operational-data handling before real exports are used.
5. Add a health endpoint that distinguishes API readiness from model readiness; bound inference timeouts and return actionable errors.
6. Record measured resource use and deployment costs from the chosen provider before estimating ongoing spend.
7. Test an end-to-end demo and provide a public demo URL only after the product and required repository visibility decision are approved.

For the sensor extension, additionally reproduce seeded historical/live-style condition facts, validate units/time/coverage and sensor mounting, handle stale/duplicate/late readings, enforce asset/document/profile applicability in graph-constrained retrieval, and pin sensor-window and knowledge versions into report evidence. Distinguish signal freshness and knowledge-index readiness from model availability. Keep synthetic-data and model live/replay/fixture indicators visible. These are future readiness checks, not achieved deployment states.

No deployment workflow is included until there is an implemented application and selected target. The current GitHub action runs repository-integrity checks only.
