# Project proposal: traceable maintenance intelligence

## Problem and intended benefit

Industrial maintenance records are often exported from different systems with inconsistent headings, abbreviations, and descriptions. Analysts must normalize them before they can compare recurring failures, components, and actions. This proposal targets a narrow job: help a maintenance supervisor convert a reviewed collection of work-order exports into a concise report whose findings can be traced to source records.

The benefit hypothesis is faster, more consistent preparation of maintenance summaries while preserving supervisor control and evidence links. We will measure task completion time and correction burden in a representative workflow before claiming time savings.

## Users and MVP

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

The MVP excludes live telemetry, automatic repair prescriptions, a manual/chatbot, and claims that connect sensor readings to work orders without validated linkage. Messy demonstration exports may be reformatted copies of the same underlying records; they must be labeled as such and must not be presented as independent samples.

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
