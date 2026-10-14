# Project proposal: sensor-informed, traceable maintenance intelligence

## Current proposed system - October 14, 2026

The user confirmed the new direction as three loops and eleven logical parts: monitor once per completed hour; respond through expert-authorised scope, feasible dispatch, recovery verification and reviewed publication; improve through offline evaluation and approved releases of extraction/reasoning LoRA adapters. Read the [complete workflow and architecture comparison](PROPOSED_SYSTEM_WORKFLOW.md) and the [current architecture section](ARCHITECTURE.md#simplified-high-level-architecture-and-fine-tuning-role---october-14-2026). All application capabilities and performance improvements remain proposed.

This section takes precedence over the historical text-only MVP and earlier training/fallback schedule below. Fine-tuning is independently evaluated by task, and model unavailability leaves numeric alerts and evidence available without silently substituting an unevaluated base-model draft. Real failure prediction remains a separately validated later phase. No factory integration, training job, deployment or automated dispatch is started by this proposal.

## Scope revision - October 13, 2026

**Confirmed user direction:** combine sensor information with RAG and knowledge-graph-assisted reasoning to improve machine-state assessment; support historical and live-style inputs; demonstrate the idea using simulated data because no factory connection is available. KAG means a knowledge-graph approach here, not a commitment to OpenSPG or another framework. No application, sensor simulator, graph, retrieval system or condition model has been implemented.

**Proposed first demonstration:** one motor-driven pump; bearing temperature, vibration RMS and motor current; speed/load and operating mode as context. Historical playback and simulated-live updates share a timestamped observation contract. Collect continuously and evaluate the last completed hour once per hour. Maintain separate views for measured/simulated observations, hourly condition/deviation facts, evidence-backed hypotheses and human-reviewed conclusions. Select sampling/feature-bucket/coverage settings and fictional demo limits explicitly before implementing; do not present them as industrial standards.

**Confirmed combined scope:** retain the previous maintenance-record workflow and continuously read machine logs plus incoming/updated CSV/XLSX exports alongside sensors. Route each source by its meaning: numeric telemetry, observed machine events or maintenance records. Use one reviewed asset registry, versioned graph and RAG pipeline for context, with exact calculations and human-approved historical records as their respective factual sources. Demonstrate with synthetic logs and a watched/polled demo export location. Checkpoint, deduplicate and preserve changed-row revisions; reports freeze source versions and as-of time. Historical triage, current condition, bounded questions, checked reports and approved coded exports belong to the combined target design; triage scoring remains provisional and Evolus remains an optional integration decision.

**Confirmed hourly feedback loop:** collect continuously; once each hour compare that completed hour with eligible earlier healthy history under matching asset/load/speed conditions. Meaningful deviations create an in-app alert, followed by RAG/graph evidence evaluation and identified expert review. Validated confirmed/corrected case findings expand a versioned case library, graph and retrieval index for later hours. Rejected/inconclusive assessments remain labeled and do not become confirmed-fault knowledge. Knowledge growth is not automatic model retraining or a silent change to normal baselines/thresholds. Data or baseline gaps produce explicit notices rather than healthy-state claims. No hourly process or notification integration is implemented.

Existing work-order parsing, review, exact counts, revisions, snapshots and claim validation remain part of the system. The condition panel and historical work-order triage answer different questions and must not share a misleading score. Evidence-linked reports still require a separate human sign-off.

Use synthetic asset-linked work orders and fictional, clearly marked demo operating guidance for the first integrated example. MaintIE remains useful for text-extraction evaluation, but must not be fabricated into sensor-linked history: it does not establish the identity/time relationships needed by this extension. Real authorized manuals and actual sensor integrations can be added after the demonstration's contracts and data rights are established.

The design and judge walkthrough are specified in [the sensor-informed architecture revision](ARCHITECTURE.md#sensor-informed-rag-and-knowledge-graph-revision---october-13-2026). The sections below retain the historical text baseline and its evaluation requirements; where that baseline excludes sensors or document retrieval, this explicit user-requested revision takes precedence for the simulated demonstration.

## Problem and intended benefit

Industrial maintenance records are often exported from different systems with inconsistent headings, abbreviations, and descriptions. Analysts must normalize them before they can compare recurring failures, components, and actions. This proposal targets a narrow job: help a maintenance supervisor convert a reviewed collection of work-order exports into a concise report whose findings can be traced to source records.

The benefit hypothesis is faster, more consistent preparation of maintenance summaries while preserving supervisor control and evidence links. We will measure task completion time and correction burden in a representative workflow before claiming time savings.

## Users and historical text baseline

Primary user: a maintenance supervisor or reliability engineer preparing an internal review from historical work orders. The supervisor remains responsible for mappings, extracted annotations, and report approval.

Proposed MVP flow:

1. Upload CSV or XLSX maintenance exports to a private application workspace.
2. Preview rows and accept or edit proposed column mappings.
3. Normalize records and assign stable source-record identifiers.
4. Suggest component, fault, and action spans/categories using an open model, retaining exact source text and offsets.
5. Review, correct, and approve each suggestion; retain actor, time, revision, and evidence.
6. Compute counts deterministically and retrieve related approved work orders.
7. Draft a narrative from a versioned fact table. Bind each numeric claim to an approved fact identifier and its scope.
8. Block unbound, unsupported, or scope-mismatched numeric claims; produce a PDF from the approved snapshot.

The historical text baseline excluded telemetry and manuals/chat. The revised simulated demo includes sensor observations and task-bounded retrieval of applicable documents/history; actual factory telemetry remains unconfigured. Automatic repair prescriptions, equipment control, unsupported diagnoses and claims linking sensors to work orders without explicit asset/time evidence remain outside scope. Messy demonstration exports may be reformatted copies of the same underlying records; they must be labeled as such and must not be presented as independent samples.

## Evidence and dataset plan

The source idea document, “AMD ACT III idea document,” dated October 8, 2026, proposes maintenance-text extraction and references MaintIE. The MaintIE repository describes 1,076 fine-grained annotated texts and 7,000 coarse-grained texts, with five top-level classes, 224 leaf classes, and six relation types. Its repository states an MIT license. These counts describe the published resource, not this project's training data or expected performance: [MaintIE project](https://github.com/nlp-tlp/maintie).

Use MaintIE's published train/validation/test organization where licensing and format permit. Keep its test split untouched through tuning, including any pseudo-label generation. Report named-entity span and relation results separately from any projection into this project's simpler component/fault/action categories. State taxonomy mapping rules and ambiguous cases; report confidence intervals where practical, and distinguish cold-start from warm inference latency. Reproduce the source document's baseline only after identifying its data split, exact metric, and preprocessing; do not repeat its figures as established results.

MaintIE's published results describe a 108-text randomly sampled test set and include a 224-class entity-table micro F1 of 27.32 for one experiment; this is dataset-specific reference context, not a directly comparable target for this project's projected labels: [MaintIE results](https://github.com/nlp-tlp/maintie/blob/main/RESULTS.md).

For product evaluation, use a separately held-out set of authorized work orders, split by machine or time where possible. Record annotation guidance, reviewer agreement, correction rate, unsupported-claim rate, report completion time, and end-to-end latency. Do not treat reformatted copies as new independent examples.

## Later thermal and prediction research

Thermal heat-map anomaly detection is a future phase, separate from the text MVP. It requires real thermal data with labels confirmed by qualified review, machine identity, timestamps, operating load, ambient conditions, camera setup, and maintenance outcomes where available. Split evaluation by asset and time to expose generalization; compare against a simple baseline and report class-specific recall/precision, false alerts per operating interval, and uncertainty. A visual heat map is an explanation aid, not proof of a fault.

Failure prediction is a later and distinct objective. It requires reliable event/outcome labels, time-aware feature construction, censoring and missingness rules, and an asset/time-held-out evaluation. Anomaly detection does not by itself establish a predicted failure. Do not connect thermal observations to a work order unless a reviewed, timestamped linkage exists.

## Proposed workstreams and schedule

The source plan proposes three parallel workstreams across six days: (A) ingestion, deterministic analytics, and report assembly; (B) model adaptation and serving; (C) interface, integration, and demo. First 12-hour checkpoint: establish a reachable inference endpoint and verify structured JSON extraction on a small smoke set. If adaptation or serving fails, use a merged adapter or a documented few-shot baseline, and report which path was actually used. A Track 3 pivot is a team decision, not an automatic fallback.

The original plan estimates 37–48 GPU-hours. This is an unverified estimate, not an available quota or entitlement. Confirm access and runtime before committing to a schedule. Prioritize a working end-to-end workload; the challenge page describes Track 1 as Intelligent Industry and expects a meaningful AMD workload. The reviewed event page lists a final submission time of October 18, 2026 at 15:00 UTC (22:00 Bangkok); recheck the live event page before relying on dates or rules: [challenge details](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii), [live schedule](https://lablab.ai/ai-hackathons/amd-developer-hackathon-act-iii/live).

## Proposed stack

Python data and service layer; pandas/openpyxl for tabular ingestion; SQLite for a single-user/demo prototype with migrations and stable IDs; PyTorch/PEFT LoRA for adaptation; AMD ROCm and an AMD MI300X environment if confirmed; vLLM for serving if the selected model and structured-output path are compatible; ReportLab for PDF generation; a browser client calling a server-side API proxy. Candidate models, hardware availability, runtime images, and latency must be tested in the actual environment. AMD documents a ROCm vLLM ecosystem path, but this does not guarantee compatibility for a particular model, image, adapter, or constrained JSON mode: [AMD ROCm vLLM documentation](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/inference/vllm.html).

Evolus may be evaluated as an optional workflow, extractor, or model library only after confirming it fits the data and deployment contract. It is not a dependency of the MVP decision.

## Risks and mitigations

- **Noisy extraction:** preserve exact spans and source IDs; require human approval; evaluate by class and source.
- **Misleading reporting:** use a versioned fact table and typed claim-to-fact references; prohibit unsupported numeric prose; validate before rendering.
- **Data leakage:** keep published test data out of all tuning and pseudo-label loops; split product evaluation by asset/time.
- **GPU or model incompatibility:** run a bounded smoke test early and use a clearly labeled baseline fallback.
- **Sensitive work-order exports:** minimize retained data, document retention/deletion behavior before implementation, and keep secrets and datasets out of Git.
- **Thermal overclaim:** treat thermal work as future research until labeled data and a valid asset/time-held-out evaluation exist.

## Success criteria for a first demonstrator

A reviewer can upload a documented sample, correct mappings and extracted fields, approve a fixed record set, inspect each report fact's supporting record IDs, and download a PDF. Re-running analytics over the same approved snapshot yields identical values. Unsupported numeric claims are blocked. The demo identifies which model path was run and reports measured latency and evaluation scope without implying production readiness.

For the sensor extension, the same seeded scenario produces the same condition facts in historical playback and simulated-live mode. A judge can inspect the observation window, sensor-to-component graph paths, retrieved guidance and work-order citations behind each explanation. Missing/stale data produces an explicit insufficient-data state; incorrect asset or document applicability is excluded. Sensor readings and demo limits are marked simulated, hypotheses remain separate from confirmed faults, and unsupported diagnostic or predictive language blocks issued reports. These are acceptance criteria, not completed checks.
