# Proposed system: hourly monitoring, expert-led response and evaluated model improvement

## Status and purpose

**Proposed system; direction confirmed on 14 October 2026.** This issue records the new IGNIS system for team review and future implementation. It does not claim a working application, a trained adapter, GPU access, valid industrial forecasts or measured production savings. The demonstration data and numerical examples are synthetic.

Shared proposal assignees: @khanhtuongnakitomo, @UniverseScripts and @BennedictQuanTon. All three are assigned for joint review and coordination; individual implementation-stream ownership is still to be agreed rather than inferred from usernames.

This proposal extends the work-order/report foundation in #1 and #2. The earlier build tracker #11 remains historical where its full-fine-tuning plan, schedule and model fallback differ. This issue does not close or rewrite those issues and does not approve their deployment or optional integrations.

## Reviewable sources

- [Complete workflow, comparisons, worked examples and acceptance criteria](https://github.com/khanhtuongnakitomo/IGNIS/blob/docs/proposed-three-loop-system-2026-10-14/docs/PROPOSED_SYSTEM_WORKFLOW.md)
- [Current architecture specification](https://github.com/khanhtuongnakitomo/IGNIS/blob/docs/proposed-three-loop-system-2026-10-14/docs/ARCHITECTURE.md)
- [Hospital analogy and design rationale](https://github.com/khanhtuongnakitomo/IGNIS/blob/docs/proposed-three-loop-system-2026-10-14/artifacts/ignis-architecture-explained.html)
- [Eleven-part interactive walkthrough source](https://github.com/khanhtuongnakitomo/IGNIS/blob/docs/proposed-three-loop-system-2026-10-14/artifacts/ignis-high-level-architecture.html)

The review branch is `docs/proposed-three-loop-system-2026-10-14`; it is not a merged implementation on `main`. The HTML artifacts illustrate a design. Open a local copy to run their controls; a GitHub source page is not an application deployment.

## Proposed architecture and workflow

### Monitor: six parts

1. **Sources:** continuously collect synthetic sensor readings, machine logs, maintenance exports and applicable manuals. Historical playback and simulated-live mode share contracts.
2. **Ingest & review:** validate units, timestamps and asset identity; review column mappings; use an extraction LoRA adapter to suggest component/fault/action spans, then obtain supervisor correction/approval. Preserve raw records, provenance and revisions; manual annotation remains available during model outages.
3. **Trusted data:** retain validated observations, approved history, asset/component/sensor/manual relationships, snapshots and retrieval indexes as versioned trusted state. Measurements, computed facts, hypotheses and expert findings remain distinct.
4. **Hourly check:** assess exactly the previous completed hour, such as `[09:00, 10:00)` at 10:00. Compare appropriate features with an eligible healthy baseline for the same asset/regime. Emit normal, insufficient-data or numeric-deviation states. Raise an alert before any LLM call; repeated hours link to an incident. Conditional threshold extrapolation is not failure-time prediction.
5. **Evidence & explanation:** resolve applicable asset/manual relationships through the graph, retrieve scoped passages/cases with RAG, freeze an evidence pack, and request cited hypotheses/uncertainty/inspection suggestions or abstention from the reasoning adapter. Validate citation and typed entity/unit/time/fact bindings. A failed or unavailable model leaves alerts and available evidence accessible to experts.
6. **Reports:** render numbers from typed facts; retain pinned evidence; obtain human sign-off and validate exports. Reports are an output branch, never an alert-release gate.

### Respond: four parts

7. **Incident & expert:** assign one owner; record confirmed/corrected/rejected/inconclusive outcomes and authorised inspection/repair scope. Acknowledgement is distinct from confirmation. The model has no approval authority.
8. **Match & dispatch:** enforce qualifications, permits, resources and calendar constraints first. Compare feasible assignments across jobs by calculated production loss. Dispatcher approval and technician acceptance precede booking; revision conflicts and declines cause replanning. No qualified resource produces visible escalation.
9. **Repair & verify:** record actual work/findings/times, then check recovery against approved criteria and later observations. Work-complete is not incident-closed. Failed or insufficient verification returns the case to investigation.
10. **Learn & publish:** review and publish versioned accepted findings for future retrieval. Retain rejected/inconclusive outcomes as labelled audit/evaluation examples, not confirmed faults. Correct/retract through supersession; publication never retrains the model or silently changes baselines.

### Improve: one part with four internal steps

11. **Fine-tuning & model release:** curate reviewed versioned examples → train two task-specific LoRA adapters on a frozen open base → compare against the untuned baseline on held-out data → obtain model-owner approval and record rollback. Extraction uses span/schema metrics; reasoning uses citation support, unsupported-claim and abstention metrics. Preserve MaintIE's published splits; use asset/time separation for additional asset-linked cases. Define release thresholds before scoring.

The proposed base model is a 7–8B size class, not a selected model. MI300X/ROCm and vLLM serving are candidates requiring access and compatibility smoke tests. No runtime, hardware purchase, training run, external integration, publication or deployment is started by this issue.

Eleven parts are logical responsibilities, not eleven required microservices. A small application/API and worker with explicit contracts is the proposed first implementation shape.

## Why this direction is stronger for the intended job

| Improvement | Mechanism | Tradeoff or proof still required |
|---|---|---|
| Broader operational usefulness | Connect monitoring to investigation, feasible work and verified recovery, beyond retrospective reports | More scope and review/resource data; measure restoration outcomes |
| Failure isolation | Alerts and deterministic calculations do not depend on model availability or training | More manual expert work during outage; demonstrate the degraded path |
| More applicable evidence | Graph resolves the correct component/model/manual before retrieval | Graph metadata and versions must be maintained; test wrong-manual cases |
| Checkable decisions | Frozen evidence, typed claims, reviewer attribution and immutable reports | Binding validation does not prove causality; expert review is still necessary |
| Better feasible scheduling | Hard qualification constraints plus cross-job production-loss comparison | Requires reliable calendars, loss rates and duration estimates; compare fair baselines |
| Stronger closure and learning | Recovery is checked; accepted knowledge and model releases have separate gates | Review effort and release delays; test failed repairs and uncertain outcomes |
| Task-specific model changes | Separate extraction/reasoning datasets, metrics, release and rollback | LoRA benefit is unproven until baseline evaluation |
| Clearer high-level explanation | Three speeds and eleven owner/gate boundaries instead of a dense block inventory | Folded engineering detail still needs implementation |

The previous architecture already had deterministic analytics, human review and evidence-linked reports. This proposal retains them. It does not claim that a graph or fine-tuning guarantees better accuracy. Hourly monitoring is not a replacement for a required rapid protection system.

## Exact synthetic dispatch example

A is unqualified and excluded. J1 and J2 are already stopped; their fictional loss rates are $1,200/h and $300/h. B waits 10 minutes; C is free now. Job-specific travel/repair durations give B→J1 60 minutes, C→J1 50, B→J2 50 and C→J2 40.

- B→J1 + C→J2: $1,200 × 60/60 + $300 × 40/60 = **$1,400**.
- C→J1 + B→J2: $1,200 × 50/60 + $300 × 50/60 = **$1,250**.

The second pairing reduces modeled loss by $150 in this restricted fixture. Calculate both outcomes from inputs. This is not measured plant savings or a production-scale optimality claim.

## Proposed implementation acceptance checklist

All items are pending; issue creation is not evidence of completion.

- [ ] Agree stream owners and a bounded synthetic vertical slice; retain the three loops and all human authority boundaries.
- [ ] Define source/asset identities, reviewed mappings, units, event-time/finalisation/late-event policy and revision/idempotency contracts.
- [ ] Build hourly deterministic assessments; replay identical seeded history/live inputs; handle normal, stale/missing-data and missing-baseline outcomes; prevent baseline leakage.
- [ ] Verify graph applicability and retrieval; freeze evidence; reject wrong asset/unit/time/number/citation bindings and expose missing evidence.
- [ ] Demonstrate model outage and rejected draft while numeric alerts and manual expert review remain usable.
- [ ] Implement attributed expert scope and incident deduplication; unknown cause may lead to approved inspection, never an invented diagnosis.
- [ ] Implement feasible dispatch, calculated $1,400/$1,250 fixture, approval/acceptance, conflict/decline handling and no-qualified-resource escalation.
- [ ] Record actual work, verify recovery, exercise failed-repair and insufficient-verification branches, then separately approve case publication.
- [ ] Publish accepted graph/index revisions consistently; preserve rejected/inconclusive outcomes and correction/retraction history.
- [ ] Generate signed-off evidence-linked PDF/CSV outputs; inspect rendered PDF and preserve drafts on validation/rendering failure.
- [ ] Confirm dataset rights/taxonomy/splits, runtime and AMD access; curate task datasets and define release gates before scoring.
- [ ] Evaluate both adapters against the untuned baseline; record versions/metrics/limitations; approve only qualifying releases and exercise rollback.
- [ ] Compare detection/explanation/dispatch outcomes separately; label every result synthetic or real; do not claim production readiness.

## Decisions still open

Base model and storage/index stack; valid thresholds/baselines and coverage; late-data and incident policies; recovery criteria; resource/qualification authorities; loss/duration inputs; numerical release criteria; and authorised real data. A rapid critical-alert path is optional and off by default. Real failure prediction needs a separate labelled-data evaluation.

This issue proposes future work. Existing repository checks validate documentation links/configuration and checker behavior; they do not exercise the future maintenance application.
