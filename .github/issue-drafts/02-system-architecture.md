# System architecture and implementation plan

This is a proposed architecture for the traceable maintenance intelligence demonstrator. No application or runtime has been implemented or compatibility-tested yet. Full rationale and data contracts: [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md); deployment gates: [docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md).

## Proposed stack

- Browser review client: React + TypeScript + Vite, provisionally recommended for typed forms and responsive review workflow.
- API/service: Python + FastAPI REST, provisionally recommended to keep tabular parsing, model adapters, analytics, and report generation in one language stack.
- Ingestion: pandas + openpyxl for CSV/XLSX, with bounded file limits and stable source record IDs.
- Prototype persistence: SQLite for a single-user/demo process; decide on a managed relational store and protected object storage before multi-user operational data.
- Model path: PyTorch/PEFT LoRA adaptation; candidate AMD ROCm/MI300X host and vLLM serving only after actual model/image/adapter/structured-output smoke tests. Embedding generation may use GPU; frozen approved-record vector retrieval runs in CPU memory.
- Reports: ReportLab PDF. API owns credentials and storage access; browser never receives provider secrets.

Every technology and threshold is provisional until a clean setup and runtime smoke test succeed. GPU hours and access are unverified.

## Architecture and data flow

1. Supervisor uploads historical CSV/XLSX. API creates an import job; parser previews records; supervisor accepts/edits a versioned column mapping.
2. Extraction worker produces schema-constrained component/fault/action suggestions with exact source text and offsets. Confidence is nullable and its meaning/calibration is recorded only if established.
3. API records corrections, approval/rejection, reviewer and revision. The browser never writes directly to the database. Model failure leaves manual review available and reports retryable per-record status.
4. An explicit snapshot operation selects approved record revisions. CPU deterministic queries compute counts. GPU-generated embeddings are indexed into a frozen, versioned snapshot index; CPU in-memory vector search retrieves similar approved records. Similarity is ranked evidence, never a count or proof of equivalence. Both count and retrieved records carry source IDs.
5. Drafting receives only the deterministic fact table and permitted retrieved citations. Quantitative claims bind typed value to supporting fact IDs, entity, metric, unit, grouping, and time scope. Quantitative prose uses deterministic templates, including spelled-out quantities. Arbitrary numeric assertions in narrative are rejected unless converted into valid typed claims. Matching a number token alone is insufficient; any unsupported or scope-mismatched claim blocks the final PDF.
6. The approved PDF stores snapshot/index/model and source-record references. A changed mapping or annotation creates a new snapshot; prior reports stay tied to their original evidence.

Provisional API: `POST /api/v1/imports`, `GET /api/v1/imports/{id}`, `PUT /api/v1/imports/{id}/mapping`, `POST /api/v1/imports/{id}/extractions`, `GET /api/v1/jobs/{id}`, `PUT /api/v1/annotations/{id}`, annotation `/approve` and `/reject` actions, `POST /api/v1/snapshots`, `GET /api/v1/snapshots/{id}`, `POST /api/v1/reports`, report status and validated-PDF reads. Writes require authentication/authorization, actor/request IDs, optimistic revision checks, and retry-safe idempotency keys before real deployment.

## Workflow and readiness

CI job `Repository checks` parses YAML/JSON, checks local Markdown links, and runs focused tests. It is not an application test suite or security scan. Product delivery sequence: agree data rights/sample and review policy; implement import/mapping/review/audit; implement deterministic facts and CPU retrieval using synthetic fixtures; smoke-test ROCm/model/adapter/JSON output on target hardware; compare extraction with fixture/offline replay and report any live few-shot LLM baseline separately (few-shot inference is not deterministic); integrate typed claim validation and PDF; test retry/restart/failure recovery; run held-out evaluation and inspect the demo artifact. API readiness and model readiness are distinct; model unavailability must not disable review and deterministic work.

Evaluation plan:

- Validate structured schemas, offsets, exact span/source matching, labels, idempotency, revision audit, and partial batch retry.
- For MaintIE, preserve its published test split from tuning and pseudo-labels; report entity spans/relations separately from component/fault/action projection, with mapping rules, per-class outcomes, and uncertainty. Confirm dataset rights and split before use.
- For vector retrieval, build judged relevant-record queries; report recall@k, precision@k, and latency by frozen embedding/index version. Do not describe retrieval similarity as factual truth.
- For claims, test correct claims and adversarial wrong entity, unit, date range, grouping, spelled-out number, unsupported number, and unrelated-fact-number cases; unresolved assertions block final rendering.
- On authorized product records, split by asset or time where feasible; report reviewer agreement, correction rate, unsupported-claim rate, task time, cold/warm inference latency, and end-to-end latency. No benchmark is claimed yet.

## Future roadmap and boundaries

MVP: historical work-order exports, human-reviewed extraction, deterministic counts, same-snapshot retrieval, evidence-bound reports. Later phase: thermal heat-map anomaly detection only after acquiring authorized real thermal images with qualified labels, machine/time/load/environment/camera metadata; use asset/time-held-out evaluation and false-alert rate. Still later: failure prediction needs reliable outcome labels, time-aware censoring/missingness handling, and separate asset/time evaluation. A thermal score is not a confirmed failure; do not link it to a work order without reviewed timestamped evidence. No live telemetry, repair prescription, or manual/chatbot in MVP.

## Acceptance criteria

- Every suggestion and report fact traces to source record and revision IDs.
- Counts and vector retrieval derive from the same approved snapshot, with exact counts distinguished from approximate ranked retrieval.
- Typed quantitative claims bind correct entity/metric/unit/group/time scope and factual rows; unsupported narrative numbers fail closed.
- API owns review and approval transitions; model outage preserves manual review and deterministic analytics.
- Selected ROCm/model/runtime succeeds on an actual structured-output smoke test before compatibility is claimed.
- Data rights, access, retention/deletion, backups, and logging decisions are set before operational exports are accepted.
- Evaluation records held-out split, data/model/index revisions, metrics, limitations, and measured latency.

## `main` branch ruleset request

When supported by the private repository plan, require pull requests with one approval, dismiss stale approvals after new commits, require code-owner review, resolve review conversations, require the strict `Repository checks` status, require linear history, and block branch deletion and force-push. Configure repository administrators (role ID 5) as the only bypass actor so initial maintenance remains possible. Verify which rules GitHub accepts and actually enforces before describing the branch as protected.
