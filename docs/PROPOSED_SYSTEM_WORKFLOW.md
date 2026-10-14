# IGNIS proposed system: workflow, rationale and acceptance criteria

**Direction confirmed:** 14 October 2026. **Implementation status:** proposed. The repository contains architecture documents and HTML illustrations; the operational services, adapters and evaluations described here are not implemented. All demonstration observations, limits, cases, resources and prices are synthetic.

**Team tracking:** [proposal issue #12](https://github.com/khanhtuongnakitomo/IGNIS/issues/12), jointly assigned to all three available repository assignees; implementation-stream ownership is still open.

IGNIS is proposed as an evidence-based maintenance system that connects machine-condition monitoring to expert investigation, feasible maintenance assignments, recovery verification and reviewed knowledge. Its intended benefit is better-supported maintenance decisions and lower production loss. These are hypotheses to measure, not demonstrated improvements.

This document explains the current [architecture specification](ARCHITECTURE.md#simplified-high-level-architecture-and-fine-tuning-role---october-14-2026), the [hospital analogy](../artifacts/ignis-architecture-explained.html) and the [eleven-part walkthrough](../artifacts/ignis-high-level-architecture.html). The [maintenance direction](MAINTENANCE_DIRECTION.md) supplies operational detail. Earlier schedules and the detailed 36-block map are historical context where they differ from this direction; the detailed map has not been updated for fine-tuning.

## 1. Three loops, eleven logical parts

| Loop | Parts | Trigger and authority |
|---|---|---|
| Monitor | Sources; Ingest & review; Trusted data; Hourly check; Evidence & explanation; Reports | Continuous collection; one assessment per completed hour. Numeric alerts do not depend on a language model. Reports require sign-off. |
| Respond | Incident & expert; Match & dispatch; Repair & verify; Learn & publish | An alert opens or updates an incident. People authorise scope, approve assignments, accept work, confirm recovery and publish reviewed knowledge. |
| Improve | Fine-tuning & model release | A deliberate offline cycle when sufficient reviewed data exists: curate, train, evaluate, approve and register. |

These are responsibility boundaries, not a requirement to deploy eleven microservices. A bounded prototype can keep related modules in one application with explicit records and job boundaries. The loops exchange versioned alerts/evidence, reviewed cases and approved model releases. Training never blocks an hourly assessment.

## 2. Monitor: from mixed inputs to an accountable assessment

### Step 1: collect continuously

Sources provide sensor observations, machine events, maintenance exports and applicable manuals. The first proposed asset is a motor-driven pump with temperature, vibration RMS and motor current, plus speed/load/operating mode. These are demo recommendations, not installed equipment.

Every record retains source identity, asset/sensor identity, event time, unit, content/version references and a synthetic flag. Checkpoint source progress, deduplicate retries and preserve revisions when an export changes. Do not infer a work-order/sensor link just because two descriptions sound similar. Historical playback and simulated-live ingestion use the same contracts and explicitly labelled simulation clock.

### Step 2: validate and review meaning

Validate schema, units, timestamps and asset identity. A person reviews spreadsheet column mappings so a temperature column cannot silently become a maintenance count. Sensor/event validation is distinct from human approval of text annotations.

The extraction adapter proposes component, fault and action spans as strict JSON with exact source offsets. A supervisor approves, corrects or rejects the suggestions. Preserve raw text, proposed labels, reviewer identity, decision time and revision. If the adapter is unavailable, manual annotation remains available.

### Step 3: maintain trusted, versioned state

Trusted data includes validated observations, approved work orders, asset relationships, manuals, reviewed cases and versioned retrieval indexes. It is one logical source of truth; physical database and index choices remain open. Keep observed measurements, computed facts, model hypotheses and expert findings distinguishable.

Create immutable snapshots for downstream work. A later correction creates a new revision, preserving the evidence used by a prior assessment or issued report. Publish graph and retrieval updates consistently; if an update fails, keep the prior retrieval view active.

### Step 4: seal and assess one completed hour

At 10:00 Bangkok time, assess `[09:00, 10:00)`, selecting by event time with explicit timezone/UTC handling. Features can include trends, extrema, persistence and event counts; a mean alone can hide a short excursion. Compare against an approved baseline matching the asset, units, configuration and operating regime.

Eligible baseline history excludes the current interval, future information, known abnormal intervals and bad observations. Domain-approved absolute limits are a separate check. A repeated abnormal pattern does not become healthy automatically.

The result is one of three branches:

- **Adequate data, no meaningful deviation:** record the assessment and continue monitoring.
- **Insufficient or stale data/baseline:** record a quality notice with missing evidence; do not label the asset healthy or invent a fault.
- **Meaningful deviation:** create a numeric alert and open or update its incident before explanation generation.

The alert carries asset, interval, measured features, quality, source IDs and baseline/rule versions. Repeated alerting hours from the same incident link to that incident. A corrected completed window creates a linked revision. Finalisation grace, coverage, incident deduplication and late-event policy need explicit implementation choices.

A straight-line threshold-crossing estimate is optional bounded numeric output. It is conditional on the trend continuing, not a remaining useful life, failure time or failure probability. The optional rapid critical-alert route remains off by default and does not authorise equipment shutdown.

### Step 5: gather evidence and draft an explanation

The knowledge graph resolves sensor → component → asset/model → applicable manual, including relevant versions and scope. RAG then retrieves permitted passages and reviewed history within that applicability boundary. A graph relationship establishes recorded applicability, not physical causation.

Freeze observations, computed facts, passages and graph paths into an evidence pack with stable item IDs. The reasoning adapter receives this pack and returns structured hypotheses, supporting/conflicting evidence, uncertainty and a suggested inspection, or explicit abstention.

Code checks schema, citation resolution and typed claim bindings: entity, metric, unit, grouping, time interval and fact version. A matching number appearing somewhere in the pack is insufficient. These checks can disprove unsupported factual bindings; they cannot prove that a causal hypothesis is correct. Expert review remains necessary.

If generation fails, the adapter is unavailable or a draft fails validation, the alert and available evidence still reach the expert. Missing evidence is exposed. Do not silently serve an unevaluated base-model replacement.

### Step 6: issue reports from pinned evidence

Report numbers render from typed computed facts. A model may draft narrative, but unsupported assertions must be removed or corrected before approval. A named reviewer signs off; PDF/CSV outputs retain snapshot, source, graph/index and model references. Rendering failure leaves a draft/error, never an approved output. Issued reports retain their original evidence when later data changes.

Reporting is an output branch of monitoring and response, not a prerequisite for releasing an alert or starting expert review.

## 3. Respond: from alert to verified maintenance outcome

### Step 7: establish incident ownership and expert scope

Assign one accountable incident owner. The expert can confirm, correct, reject or mark the explanation inconclusive, recording reason, evidence and revision. Acknowledgement is not diagnosis confirmation. Abnormal condition may be confirmed while its cause remains unknown.

The expert authorises a bounded task, such as inspecting mounting and checking for wear. The model's suggestion does not authorise a repair. Missing evidence can justify an approved inspection; it cannot justify inventing a diagnosis.

### Step 8: propose a feasible assignment

Construct a job from the authorised scope, asset state and required qualifications/resources. Filter out ineligible technicians before calculating cost: qualifications, permits, availability, parts/tools and scheduling constraints are hard rules.

Among feasible assignments, calculate estimated production loss across competing jobs. Running, reduced-output and stopped assets need different costing; travel is not automatically downtime for a running asset. A two-job demo can enumerate both assignments transparently. A larger constraint solver is a later choice when crews, parts and calendars compete.

The dispatcher approves the plan and the assigned technician accepts. Recheck resource/calendar revisions before booking. Conflicts, declines and missing resources invalidate affected candidates and cause replanning; if no eligible resource exists, leave the job unassigned and escalate. A cheap infeasible assignment is never valid.

### Step 9: perform work, then verify recovery

Record actual inspection findings, action, parts, timestamps and technician attribution. Keep estimates separate from actual durations and loss.

Work-complete is not incident-closed. Assess later observations against an approved recovery criterion and obtain the verification decision. Recovery duration, features and approver roles need definition. A failed or insufficient verification keeps the incident open or returns it to investigation; it cannot become a successful-repair case.

### Step 10: review and publish a case

A reviewer checks the conclusion, evidence, applicability and repair/recovery outcome before publication. Versioned accepted findings become searchable cases and supported graph relationships. Corrections/retractions supersede prior versions without erasing history.

Rejected and inconclusive outcomes remain labelled in the audit/evaluation ledger. They can be curated as negative or abstention examples, but are not indexed as confirmed faults. Publishing accepted knowledge makes it available to retrieval immediately. It does not retrain weights, revise thresholds or change a healthy baseline.

## 4. Improve: evaluated task adaptation, separately from current facts

One proposed open base model carries two independent LoRA task adapters:

| Adapter | Input/output | Evaluation |
|---|---|---|
| Extraction | Work-order text → component/fault/action spans, labels and exact offsets in JSON | Span F1, per-class results, schema validity and reviewer correction burden |
| Reasoning | Frozen evidence pack → cited hypotheses, uncertainty, inspection suggestion or abstention | Citation accuracy, unsupported-claim rate and correct abstention on reviewed cases |

Fine-tuning is intended to improve task format, vocabulary and evidence discipline. Today's measurements, asset facts and manuals still come from trusted state and retrieval. Whether adaptation improves performance is an experiment, not an assumed result.

1. **Curate:** verify data rights and taxonomy; version reviewed examples. Preserve MaintIE's published train/validation/test organization and keep its test split out of tuning. For additional asset-linked product cases, split by asset/time and keep related incidents or reformatted copies together; do not fabricate asset metadata for MaintIE.
2. **Train:** supervise each adapter on its own task while freezing base weights. The proposed 7–8B model, MI300X/ROCm runtime and vLLM adapter serving require selection and real compatibility/access checks. No GPU job is launched by adopting this proposal.
3. **Evaluate:** compare adapters with the untuned baseline on the same held-out cases, with the same input evidence and prompting conditions. Set acceptance thresholds and safety regression limits before scoring. Training loss alone does not qualify a release.
4. **Approve and register:** a named model owner approves or rejects. Record base/adapter/data versions, runtime configuration, results, approver and rollback target. Extraction and reasoning releases can be independent. A failed candidate stays offline.

Training is deliberate rather than tied to hourly alerts or case publication. Numeric rule/baseline changes require a separate attributed approval and effective version, even if managed within the same high-level release block. Model weights do not set operational thresholds.

## 5. Worked synthetic incident

Temperature hourly means rise from 72 to 76 to 80 °C. The slope is +4 °C/hour. Under the fixture's explicit convention that 80 °C is the trend value at 10:00, the fictional 85 °C limit is 5/4 = 1.25 hours away, or 11:15. Hourly means have their own interval timestamps; a real implementation must define the trend's reference time rather than silently treating an interval mean as an instantaneous endpoint. This is a conditional example, not a physical failure prediction.

At the completed-hour boundary, code raises an alert. The graph selects applicable pump guidance; retrieval provides passages and reviewed cases; the adapter proposes cited mounting/wear hypotheses. The expert approves an inspection scope.

For the separate stopped-asset dispatch fixture, J1 loses $1,200/hour and J2 $300/hour. A is unqualified and is excluded. Both jobs stopped at 10:00; B waits 10 minutes and C is available immediately. Travel and repair times depend on the technician/job pairing:

| Technician | J1: travel + repair + wait | J2: travel + repair + wait |
|---|---|---|
| B | 20 + 30 + 10 = 60 minutes | 10 + 30 + 10 = 50 minutes |
| C | 30 + 20 + 0 = 50 minutes | 20 + 20 + 0 = 40 minutes |

| Feasible plan | Calculated modeled loss |
|---|---|
| B → J1, C → J2 | $1,200 × 60/60 + $300 × 40/60 = $1,400 |
| C → J1, B → J2 | $1,200 × 50/60 + $300 × 50/60 = $1,250 |

The preferred pairing saves $150 within this fixture. It is optimal among these two feasible parallel pairings, not across an entire factory. Calculate outputs from the job-specific input matrix; do not hardcode the selected result. These are fictional estimates, not measured savings.

After work, recovery must be verified. A reviewed successful case becomes retrieval context for a later alert. It is only a candidate for a future training cycle.

## 6. Where the architecture is stronger, and what it costs

The comparisons below are design arguments against the earlier text/report-only scope, an LLM-led monitoring pipeline, or a dense one-way diagram. They are not measured claims against deployed alternatives. The older design already preserved human review, deterministic counts and evidence-linked reporting; those protections are retained rather than newly invented.

| Dimension | Why the new direction is stronger for this job | Cost or limit | Evidence needed |
|---|---|---|---|
| Operational coverage | Connects present condition to investigation, assignment and verified recovery, beyond retrospective work-order summaries | Larger scope, more resource/outcome data and more review screens | Demonstrate one complete incident; measure time to inspection/restoration |
| Availability | Numeric alert creation is independent of explanation and training | Experts do more manual investigation during outages | Inject model failure; prove the alert and review still work |
| Applicability | Graph-scoped retrieval reduces the opportunity to use guidance for the wrong model/component | Graph maintenance and correct identity/version metadata | Wrong-model manual and conflicting-version retrieval cases |
| Auditability | Frozen evidence, typed facts and recorded approvals expose how a decision was made | Version management, rejection handling and reviewer effort | Replay snapshots and reject wrong-unit/asset/time claims |
| Resource decisions | Eligibility constraints protect feasibility; global job comparison can outperform a local nearest-person rule | Requires qualified resource data and credible loss/duration estimates | Compare identical seeded scenarios with FIFO and nearest-eligible policies; count violations |
| Closure quality | Recovery verification prevents work-complete being treated as proof of restoration | Cases remain open longer and need defined verification criteria | Failed-repair and sensor-dropout branches |
| Knowledge quality | Only reviewed findings become accepted knowledge; training stays separately evaluated | Review backlog, release delay and negative-case curation | Rejected/inconclusive/retracted cases never become confirmed faults |
| Model specialization | Two adapters have separate task data, metrics and rollback rather than one coupled release | Dataset and serving/evaluation complexity | Beat the untuned baseline without safety regression; otherwise do not release |
| Comprehension | Eleven logical parts organised by speed, owner and gate are easier to explain than 36 implementation blocks | Detail must remain discoverable; fewer boxes do not mean less engineering | A teammate can trace the default and exception paths without confusing authority |

The system is not automatically better at every job. A historical report-only tool is cheaper when monitoring and dispatch are unnecessary. An hourly monitor has delayed response and is unsuitable as a substitute for a required fast protection system. RAG relevance does not prove truth, claim checks do not prove causality, and LoRA does not guarantee an improvement. Production benefits require observed outcomes and fair comparisons.

## 7. Proposed delivery order and definition of done

| Stage | Reviewable outcome and meaningful checks |
|---|---|
| 1. Trusted monitoring | Seeded pump, reviewed mappings, provenance and hourly worker; historical/live replay produces identical facts; duplicate/late/stale cases and missing baseline handled |
| 2. Evidence and expert review | Graph applicability, retrieval, pinned evidence and attributed scope; wrong-manual and unsupported-claim checks; model outage retains alerts |
| 3. Dispatch | Qualification filters, calculated two-job fixture, approval/acceptance and revision-checked booking; infeasible, stale-calendar and decline branches |
| 4. Recovery and knowledge | Actual work records, failed/successful recovery, separate publication; supersession and rejected/inconclusive outcomes handled |
| 5. Reports | Typed numbers, evidence references, sign-off and inspected PDF; failed generation cannot produce an approved report |
| 6. Adapter qualification | Curated datasets, honest holdouts, baseline comparison, approved registry and exercised rollback; hardware/serving evidence recorded |

A functional manual/synthetic vertical slice should precede reliance on fine-tuning. It can proceed while adapter experiments are prepared. Logical stages are dependencies, not committed dates or allocated owners.

Open decisions: selected base model and runtime; storage/index stack; approved rules/baselines and data-quality thresholds; finalisation/late-data policy; incident and recovery criteria; qualification/resource authorities; loss rates and duration assumptions; held-out metrics/release thresholds; authorised real data. None is established by the HTML animation.

The current repository checks validate links, source YAML/JSON and the checker itself. They do not verify the future application. Completion of this documentation or its tracking issue is not completion of the product.
