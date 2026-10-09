# Project proposal: traceable maintenance intelligence

## Problem and user

Maintenance supervisors and reliability engineers often normalize inconsistent CSV/XLSX work-order exports by hand before identifying recurring components, faults, and actions. This project proposes a review-first tool that helps them produce a concise maintenance summary whose claims can be traced to approved source records. The benefit is a hypothesis: reduce summary preparation effort without sacrificing supervisor control; measure elapsed task time and correction burden before claiming improvement.

## Proposed MVP workflow

1. Upload historical CSV/XLSX exports to a private application workspace and preview rows.
2. Have a mapping assistant suggest source-to-canonical columns; supervisor accepts or edits a versioned mapping.
3. Normalize records with stable source IDs. A model suggests component, fault, and action annotations with exact source spans and provenance.
4. Supervisor reviews, corrects, approves, or rejects suggestions; actor, timestamp, and revision remain auditable.
5. Deterministic code computes counts. Embeddings support related-work-order retrieval from the same approved snapshot; ranked similarity remains distinct from exact counts.
6. Draft a report from a versioned fact table and permitted retrieved records. Quantitative assertions bind typed values to fact IDs, entity, metric, unit, grouping, and time scope; deterministic templates render quantitative prose. Unsupported or mismatched claims block the PDF.

The MVP does not ingest live telemetry, prescribe repairs, include a manual/chatbot, or infer a sensor-to-work-order link. Demonstration files that are reformats of the same source data must be identified as such, not counted as independent examples.

## Future phases

Thermal heat-map anomaly detection is future research after obtaining authorized real thermal data with qualified labels, asset identity, timestamps, load, ambient conditions, camera setup, and outcomes where available. Evaluate on asset/time-held-out data, compare a simple baseline, report class-specific recall/precision and false alerts per operating interval, and treat visual heat maps as explanations rather than proof.

Failure prediction is a separate later objective requiring reliable outcomes, time-aware feature construction, explicit missingness/censoring rules, and asset/time-held-out evaluation. Anomaly detection alone does not establish a predicted failure. Link images or scores to work orders only when a reviewed, timestamped relationship exists.

## Data, evaluation, and evidence

The published MaintIE resource describes 1,076 fine-grained and 7,000 coarse-grained texts, five top-level classes, 224 leaves, and six relations. Its published results identify a randomly sampled 108-text test set and one 224-class table micro F1 of 27.32; that score is dataset/experiment-specific context, not a directly comparable target for our component/fault/action projection. Preserve the published test split from tuning and pseudo-label generation. Report span and relation measures separately from the projection, document mapping rules, per-class results, uncertainty where practical, and cold/warm latency. See [MaintIE data](https://github.com/nlp-tlp/maintie) and [published results](https://github.com/nlp-tlp/maintie/blob/main/RESULTS.md).

For authorized product data, split by machine or time where practical. Record annotation guidance, reviewer agreement, correction rate, unsupported-claim rate, task completion time, and end-to-end latency. Test adversarial report claims with wrong entities, units, date windows, groupings, spelled-out quantities, unsupported quantities, and a number found in an unrelated fact. Do not report unverified source-PDF benchmark figures as reproduced results.

## Proposed stack and workstreams

Provisional stack: Python with pandas/openpyxl; SQLite only for a single-user demo; PyTorch/PEFT LoRA; AMD ROCm and MI300X only if actual access is confirmed; vLLM only after testing the selected model, image, adapter, and structured-output mode; ReportLab PDFs; browser UI calling a server-side API proxy. Proposed UI/API recommendation is React + TypeScript + Vite with FastAPI REST, subject to an early workflow spike. Exact runtime compatibility remains unverified. Evolus can be evaluated as an optional workflow/model library after fit is demonstrated, not assumed as an MVP dependency.

The source plan proposes three six-day workstreams: ingestion/deterministic analytics/reporting; model adaptation/serving; UI/integration/demo. At 12 hours, smoke-test a reachable model endpoint and structured JSON extraction. If adaptation or serving fails, identify and use either a merged adapter or documented few-shot model baseline. Fixture/offline replay is a separate deterministic test path. A Track 3 pivot requires a team decision. The original 37–48 GPU-hour estimate is not an allocation or entitlement; verify access before committing.

## Risks and first-demo acceptance

Main risks: noisy extraction, unsupported report claims, train/test leakage, model/GPU incompatibility, and sensitive exports. Mitigate with source spans, human approval, immutable approved snapshots, fail-closed typed claims, test isolation, an early runtime smoke test, and explicit data handling decisions.

- Reviewer can upload a documented sample, correct mappings and annotations, approve a fixed set, inspect supporting source IDs, and download a PDF.
- Re-running deterministic analytics on one approved snapshot reproduces exact values; similarity search is labeled ranked retrieval.
- Unsupported quantitative assertions block final rendering.
- Demo identifies actual model path, versions, measured latency, and evaluation limits.
- Data rights, privacy, retention/deletion, review responsibility, team capacity, compute access, and challenge submission details are confirmed before execution.
