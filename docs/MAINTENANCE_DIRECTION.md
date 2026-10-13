# IGNIS — maintenance intelligence and dispatch direction

Date: 13 October 2026. Status: proposed product architecture and executable visual-design plan. The application, sensor adapters, forecasting models and scheduling services remain unimplemented. The interactive walkthrough demonstrates local synthetic decisions; it is not a factory integration or an industrial validation result.

This is the requested expansion of the [existing architecture](ARCHITECTURE.md) following the architecture audit. It preserves the evidence and work-order foundation while adding maintenance execution. Earlier exclusions of prediction and dispatch describe the previous scope; this document defines their proposed introduction and validation boundaries. It does not change repository instructions or authorize equipment control, deployment or publication.

## 1. Product job and definition of success

Help a supervisor recognize a developing or active machine problem, understand the evidence and uncertainty, arrange a suitable inspection or approved repair, and restore production with the least expected loss across pending jobs.

The operational unit is an incident linked to an asset, a bounded assessment and one or more maintenance jobs. The user should be able to answer:

1. What changed, and is the data trustworthy?
2. What causes are supported, contradicted or unknown?
3. Is deterioration forecastable, over which horizon, and with what limitations?
4. What inspection or approved task is needed, and by when?
5. Which qualified technician or crew can perform it with the necessary resources?
6. When can work start and production recover, and why is this schedule preferable?
7. What actually happened, and which reviewed findings should affect future decisions?

Priority order: respect authorization and job constraints; satisfy approved urgency/deadline policy; reduce estimated production loss; use travel and labor cost as further decision inputs. An unexplained anomaly score, shortest travel time or historical fault frequency alone is not the dispatch objective. Claims of an optimal schedule must state the model, input snapshot, objective and search completeness.

## 2. Decisions, assumptions and optional changes

| Topic | Working direction | Status |
|---|---|---|
| Initial setting | Synthetic motor-driven pumps; historical playback and simulated-live data | User-approved simulation; asset choice is proposed |
| Sensor signals | Bearing temperature, vibration RMS, motor current; speed/load/mode context | Proposed demonstration signals |
| Other inputs | Continuous logs and stable completed CSV/XLSX revisions; historical work orders and applicable guidance | Requested direction |
| Cadence | Continuous collection; one assessment at each hourly boundary over the previous completed hour | Confirmed and preserved |
| Rapid critical alerts | A separate simple alarm/absolute-limit lane could shorten response delay | Optional policy change, disabled in the default walkthrough |
| RAG/KAG | Retrieve applicable evidence and traverse reviewed asset/component/fault relationships | Requested; graph framework remains open |
| Learning | Expert-reviewed case publication; separate approval for baseline, threshold or model changes | Confirmed and preserved |
| New objective | Recognition, forecasting and suitable technician assignment to reduce production loss | Newly requested product direction |
| Dispatch authority | System recommends; dispatcher approves booking; technician accepts; overrides require a reason | Proposed initial behavior |
| Repair authority | Inspection can proceed with an unknown cause under an approved task scope; repair uses an approved procedure | Proposed behavior, no autonomous repair instruction generation |
| Monetary costs | Fictional hourly loss rates and duration estimates in the demo | Illustrative inputs, not plant economics |
| Real deployment | Factory adapters, actual technician calendars and equipment control | Outside this visual revamp |

Hourly-only assessment has an explicit response limit: an event at 10:01 can wait until the 11:00 assessment, plus finalization and review delays. The visualization must preserve this policy rather than silently introducing continuous diagnosis. The optional rapid-alert proposal is distinguishable from the default route and cannot imply automatic machine shutdown.

## 3. Architecture layers and their contracts

### Layer A — intake and operational identity

Inputs: simulated observations, append-only/rotating machine logs, completed file revisions, manuals, reviewed work orders, asset master data and operational scheduling records.

Adapters assign asset/component identity, event time, source ID, units, source revision and synthetic status. Spreadsheet mapping routes each row by meaning: telemetry, machine event or maintenance record. File stability, log cursors and deduplication prevent half-written files and repeated ingestion. Unknown identities or units are quarantined instead of inferred silently.

Outputs: immutable raw source versions and normalized observations/events/records. Manuals and extracted work-order findings require applicability and review before they become accepted knowledge. Raw numeric observations need integrity checks, not expert approval of every sample.

### Layer B — trusted history and condition assessment

Finalize the prior-hour window after a configured grace interval; record coverage, missing/stale values and late-event handling. Compare features such as trends, extrema and excursion duration with eligible earlier normal windows for the same asset configuration and operating regime. Keep domain-approved absolute limits distinct from historical comparisons. Exclude current/future windows and known abnormal data from the baseline.

Outputs: versioned `HourlyAssessment`, `ConditionFact`, `BaselineSnapshot` and data-quality status. Missing history or insufficient coverage produces `insufficient_data`, never a healthy result. A deviation can create an incident before any language-model call. Repeated assessments attach to the same unresolved incident where the incident identity matches.

### Layer C — diagnosis, forecasting and grounded explanation

Diagnosis and forecasting are separate components sharing the pinned facts:

- Diagnosis combines measured changes, log events, asset topology, applicable guidance and reviewed cases. It produces supported hypotheses, alternatives and a proposed inspection scope. A graph path or retrieved paragraph is evidence context, not causal proof.
- Forecasting uses a numerical, versioned method with an explicit horizon, applicability rules and uncertainty. First demonstrate a trend-to-limit estimate on synthetic degradation; do not call threshold crossing a physical failure or remaining useful life. A later fault-specific model requires failure/outcome labels, nonfailure/censored records and asset/time-held-out evaluation.
- The language model explains these results and cites the evidence pack. It does not invent measurements, generate failure probabilities, update forecasts or choose a technician through free-form text.

An `EvidencePack` freezes observation/event references, source cutoff, work-order snapshot, baseline/rule/model versions and graph/index/document revisions. Claim checks reject unsupported quantities, diagnoses or causal certainty. If retrieval or the language model fails, retain the numeric alert and a usable expert queue. If forecasting is unsupported, show an explicit abstention and continue inspection planning.

### Layer D — incident ownership, expert review and task scope

Create an incident with owner, urgency reason, acknowledgement deadline and escalation path. Acknowledgement, diagnostic confirmation and repair authorization are distinct states. Expert outcomes remain confirmed, corrected, rejected or inconclusive. Experts can confirm an abnormal condition while its cause remains unknown.

Create an inspection job under a reviewed scope without requiring a confirmed root cause. Promote it to a repair job only when the findings and approved task procedure justify that action. Required qualifications come from reviewed job requirements and approved task templates, not an unchecked model guess. Diagnostic expert and field technician are separate roles even if one person can hold both.

Outputs: `Incident`, `ExpertReview`, `MaintenanceJob` and `JobRequirements`. Each job identifies asset/component, evidence revision, task scope, approved procedure or inspection checklist, priority, target deadline, estimated duration, parts/tools/crew/access requirements and the person authorizing it.

### Layer E — loss-aware planning and resource matching

Use current operational records as the scheduling source of truth. Required data:

- Technician skills and proficiency, qualification validity, asset authorizations and crew eligibility.
- Shifts, location, existing reservations, travel time and job-specific duration estimates.
- Available or expected parts/tools, permits, access windows and production shutdown opportunities.
- Asset criticality, redundancy, production impact, operational status and approved response deadlines.

First reject ineligible assignments. Then construct feasible technician/time/crew combinations and compare schedules across pending jobs. Prevent overlaps, respect travel and shift constraints, and include resource arrival times. Expired qualifications and missing parts cannot be overridden by a high ranking score.

For a stopped asset in the synthetic example, loss equals hourly loss rate multiplied by elapsed time from recorded stoppage until estimated restoration. For a running asset, use its actual reduced-output exposure and planned stoppage separately; travel time is not automatically downtime. A probabilistic failure-loss term is permitted only with a validated probability model. In the cold start, use explicit urgency and deadline rules rather than invented probabilities.

The objective includes production loss, relevant labor/travel costs and penalties for overdue or unassigned jobs. Return infeasible/deferred jobs visibly so dropping work cannot make the objective appear better. Pin the schedule inputs and distinguish estimated restoration from actual recovery.

Start with transparent eligibility and scheduling rules. Add a constraint solver when shared resources and competing jobs warrant it. Preserve feasibility even when search is time-limited; report best feasible versus proven optimal within the declared model. Replan pending work when incidents, parts or availability change; protect started jobs from arbitrary reassignment.

### Layer F — dispatch, execution and verification

Dispatcher reviews the recommendation, alternatives and reasons for exclusions. Approval reserves a technician/time slot atomically against current revisions; stale availability causes a conflict and replanning, not double booking. The technician accepts or declines. A decline, missed acknowledgement or late arrival triggers reassignment/escalation.

Track proposed, approved, accepted, scheduled, travelling, in-progress, awaiting-parts, work-complete, verified, closed and cancelled states where applicable. Record actual timestamps, performed tasks, parts used, physical findings, deviation from the plan and downtime. Work completion does not itself prove recovery.

Post-work checks compare sensor behavior under an applicable operating regime and verify production restoration with an authorized person. An inconclusive result leaves the incident unresolved. Distinguish sensor normalization, return to operation and verified root cause.

### Layer G — reviewed learning and evaluation

Link assessment, hypotheses, expert decisions, bookings, field findings, actions and recovery evidence. Reviewed corrections supersede earlier conclusions while preserving their provenance. Rejected/uncertain alerts remain available for evaluation without becoming confirmed-fault knowledge.

Publish accepted case revisions through idempotent, versioned graph/index updates. Case publication does not change healthy baselines, thresholds or model weights. Model candidates are trained and evaluated separately, reviewed and activated as new versions with rollback. Repairs that succeed do not automatically validate every original causal claim.

## 4. Cross-cutting services and minimal deployment shape

Use one application/API and authorization boundary, one relational system of record and one background worker/scheduler initially. These are logical modules, not a requirement for seven independently deployed services. Store raw file revisions separately when needed; maintain one lightweight graph representation and a retrieval index with pinned revisions. Framework and hosting choices remain open.

The application owns state transitions, audit attribution, optimistic revision checks and booking transactions. Workers own ingestion finalization, hourly jobs, bounded inference jobs, schedule searches and knowledge publication. Durable job keys and retries make replay idempotent. The inference adapter owns provider substitution and offline fixtures; it has no expert-review, booking or publication authority.

The graph stores relatively stable semantic relationships and case evidence. Technician calendars, parts availability and booking revisions are transactional records; do not use retrieved documents as current availability. RAG/KAG explains which evidence and requirements apply, while numerical rules/models and scheduling code perform their respective calculations.

## 5. Proposed data records and boundaries

| Record | Essential contents |
|---|---|
| SourceRevision / Observation / MachineEvent | Source identity, asset, event time, units, original values, quality, revision, synthetic flag |
| HourlyAssessment / EvidencePack | Finalized interval, facts, baseline/config/model versions, source cutoff, evidence references |
| Forecast | Method/version, feature history, horizon, estimate and units, uncertainty/applicability, abstention reason |
| Incident / ExpertReview | Owner, linked assessments, priority reason, acknowledgement/escalation state, reviewer finding and evidence |
| MaintenanceJob / JobRequirements | Approved task, procedure, asset, deadline, duration estimate, qualifications, crew, parts/tools/access |
| TechnicianProfile / Availability | Skills, qualifications and expiry, authorization, shift, location and current reservations |
| ScheduleCandidate / Booking | Input snapshot, eligible assignment, time interval, objective components, solver status, approval/revision |
| WorkExecution / RecoveryVerification | Actual times, field findings, actions/parts, downtime, production restoration and verifier |
| ReviewedCase / ModelEvaluation | Superseding knowledge revision and publication status; separate model test results and activation decision |

All contracts are design candidates. Implement them incrementally rather than creating empty abstractions for every record upfront.

## 6. Demonstration scenarios and exact synthetic dispatch fixture

Keep source data synthetic and deterministic. Simulator ground-truth fault labels are hidden from the inference path. Scenario fixtures are instructional examples, not evidence of general model accuracy.

### Hourly recognition and forecasting example

At 10:00 assess the completed 09:00–10:00 window. Earlier equivalent operating windows have temperature values 72, 76 and 80 °C at successive hourly timestamps. With a fictional 85 °C limit, an explicitly simple linear extrapolation of +4 °C/hour estimates crossing in 1.25 hours, at 11:15, conditional on that trend continuing. This is a synthetic threshold-crossing forecast, not predicted bearing failure. The forecast is withheld when history, coverage or operating mode is incompatible.

Retrieved history may suggest bearing wear or loose mounting. An expert can authorize inspection without confirming either cause. After inspection, a corrected finding such as loose mounting supersedes the hypothesis only when supported by the recorded physical findings. Recovery and knowledge publication remain separate gates.

### Independent scheduling example

The dispatch view uses two already stopped assets at 10:00, separately from the running-asset forecast example. Loss rates are fictional dollars per hour; each job needs one mechanical technician. Parts, access and qualifications are valid for B and C. A is an electrician and cannot perform these mechanical jobs. B is available after 10 minutes; C is available now. There are no other bookings; one job is assigned to each eligible technician. All durations are minutes.

| Technician | J1: travel / repair / restoration after 10:00 | J2: travel / repair / restoration after 10:00 | Eligibility |
|---|---|---|---|
| A | 5 / — / — | 5 / — / — | Missing mechanical qualification; excluded |
| B | 20 / 30 / 60 | 10 / 30 / 50 | Qualified; initial wait 10 |
| C | 30 / 20 / 50 | 20 / 20 / 40 | Qualified; initial wait 0 |

J1 loses $1,200/hour and J2 loses $300/hour. Compare the two feasible parallel pairings:

- B→J1 and C→J2: $1,200 × 60/60 + $300 × 40/60 = $1,400.
- C→J1 and B→J2: $1,200 × 50/60 + $300 × 50/60 = $1,250.

Select C→J1 and B→J2 in this restricted example: $150 less modeled loss. These values must be calculated from fixture inputs, not hardcoded into the decision result. This is exhaustive comparison of two illustrative pairings, not a production optimizer or a measured plant saving. Actual scheduling requires more resources, timelines and uncertainty than this fixture.

### Exception scenarios

- Normal hour: archive the completed assessment and continue collection; no incident or dispatch.
- Insufficient/stale data: create a data-quality notice, abstain from diagnosis/forecast and prevent unjustified repair dispatch. A separately approved sensor-inspection task is possible, not automatically fabricated.
- No qualified resource: leave the maintenance job unassigned with an escalation; never fall back to A.
- Expert correction or inconclusive result: update the reviewed scope and keep uncertain causes out of confirmed knowledge.
- Booking conflict, technician decline or missing parts: invalidate the affected candidate and replan; preserve accepted/current work.
- Failed post-work verification: reopen/escalate the incident and withhold successful-repair publication.

## 7. Detailed implementation sequence

| Phase | Work and dependencies | Observable completion criteria |
|---|---|---|
| 0 — Architecture revamp, this request | Produce this plan; update the existing interactive architecture and animated walkthrough; preserve old visual sources | Layers and ownership are inspectable; default cadence stays hourly; proposed/optional/synthetic states are visible; no real integrations implied |
| 1 — Trusted monitoring | Seed asset/source identities, simulator, ingestion revisions, quality and finalized-hour comparison | Identical historical/live replay yields identical facts; duplicate/late/stale data is handled; unsupported windows abstain; no future baseline leakage |
| 2 — Evidence and response | Reviewed work-order history, graph applicability, RAG, checked explanations, incident owner/review/escalation and inspection scope | Every claim resolves to pinned evidence; alerts survive model failure; unknown cause can still lead to an approved inspection; no automatic knowledge publication |
| 3 — Feasible dispatch | Technician/job/resource records, eligibility, scheduling, dispatcher approval, booking and technician acceptance | No qualification violations or overlaps; infeasibility is visible; stale bookings conflict; competing-job fixture calculates both costs correctly |
| 4 — Execution and recovery | Field findings, timestamps, actions, verification and reviewed publication | Work-complete does not equal restored; unsuccessful verification remains open; corrected diagnoses supersede prior cases; measured downtime is distinct from estimates |
| 5 — Forecast validation | Synthetic degradation forecasts first; later authorized labels, feature pipeline, temporal/asset holdouts and calibration | Threshold crossing is labelled correctly; unsupported forecasts abstain; no simulator-label leakage; real failure predictions have independent evaluation |
| 6 — Scheduling expansion | Shared crews/tools/parts, shutdown windows and constrained search when demand warrants it | Compare with FIFO and nearest-eligible policies; report feasible/optimal status and unserved work; improve simulated loss without violating hard constraints |

Do not wait for a reliable physical-failure predictor to implement accountable incident response and dispatch. Their outcome records create the data needed to evaluate later forecasts. Conversely, adding a graph does not replace missing technician or downtime records.

## 8. Verification and success measurements

Measure detection recall, missed faults, false alerts per asset-hour and warning lead time on declared synthetic scenarios. Evaluate diagnosis evidence support separately from condition detection. Forecast evaluation must specify the horizon, leakage boundaries, error/calibration and abstention coverage; experts reviewing only alerts can create selection bias, so retain appropriate non-alert observation/outcome data.

Operational measures: acknowledgement delay, time to inspection/start/restoration, deadline misses, qualification/overlap violations, actual versus estimated durations, unresolved jobs and production loss. Compare dispatch policies over the same seeded incidents and resource snapshots. Report synthetic versus real evidence separately.

HTML checks for this request: inspect the actual rendering and keyboard controls; exercise animated play/pause/step/restart, component selection and dispatch outcomes; confirm hourly cadence and approval gates; test normal, insufficient-data and no-qualified-resource branches; inspect 320/360/736/1440-pixel layouts, light/dark themes and reduced motion; collect browser errors. Repository integrity checks cover documentation links/configuration only, not the proposed application.

## 9. Visual implementation brief

Primary editable inline source: the current thread's `ignis-architecture.html`. Preserve its original source before replacement. Keep a corresponding standalone animated architecture in `artifacts/ignis-data-flow.html`, preserving its old version before replacement. Use this document as the authoritative content for the revamp, not outdated thermal-selection state from the old visual.

Show one dominant architecture with six readable groups: sources; trusted history/condition; diagnosis/forecast/evidence; incident and job planning; resource matching/dispatch; execution/verification/learning. Distinguish independent diagnosis, forecast and scheduling responsibilities and the two return paths: reviewed cases to RAG/KAG, separately evaluated models to forecasting. Keep supporting API/store/worker roles inspectable without turning the graphic into a service inventory.

Provide compact selection and walkthrough controls, animated data movement and pause at expert/dispatcher/verification gates. Explain each block through concise selected detail: its input, work, output, owner and failure behavior. Preserve old Play/Pause, Next and Restart capabilities where useful. A user should be able to follow the default synthetic incident from source to recovery and see why human approval is distinct from model output.

Provide an inspectable dispatch decision using the two-job fixture, eligibility exclusions, both feasible pairings and the calculated selection. Show estimated loss, not claimed real savings. Include normal, insufficient-data and no-qualified-resource branches without inventing a large control dashboard. Keep the threshold forecast and stopped-asset dispatch fixtures visibly distinct.

Use accessible native controls, visible focus, themed high-contrast text, responsive layout with no page-level horizontal scrolling, and reduced-motion support. Inline source follows the maintained visualization fragment/runtime conventions. No external API/model calls, factory connections, auto-scheduling automation or backend implementation belong in this HTML.

## 10. Remaining decisions before a real application build

Agree on approved thresholds and operating regimes; response/repair deadlines and escalation roles; job templates and qualification authorities; asset loss rates and reduced-output costing; resource calendar/inventory ownership; deployment constraints; and the authorized labels/outcomes available for physical-failure prediction. These decisions do not block a clearly labelled synthetic visual demonstration.

The optional rapid critical-alert route remains a product choice. Default visualization behavior follows the confirmed once-hourly assessment. No document or visual change here creates a running monitor or grants permission to control equipment.
