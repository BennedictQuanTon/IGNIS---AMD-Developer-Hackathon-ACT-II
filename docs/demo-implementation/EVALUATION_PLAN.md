# Evidence, model and demo acceptance

The objective is to establish whether bounded context improves the explanation while numeric alerts and approval authority stay unchanged. These are proposed tests; this pack has not run the application or trained a model.

## Three different measurements

| Task | Data | Measures | What a pass establishes |
|---|---|---|---|
| Extraction | MaintIE locked dev/test | Exact entity/relation micro P/R/F1, per-class errors, schema validity, correction burden | Text extraction quality under the declared split |
| Evidence-use pilot | Industrial-Instruction's chosen config | Set-match accuracy, set precision/recall/F1, invalid-output rate | Answer-choice prediction on this synthetic QA task |
| IGNIS context and review | Independent authored/reviewed pump scenario families | Applicability, reference resolution, typed facts, abstention, expert support judgments, review state | Demo correctness and bounded explanation behavior |

Never substitute one metric for another. An answer-choice label supplies no reference explanation, so free-form diagnosis cannot be scored against it as if it were gold. ROUGE or a fluent answer alone is insufficient evidence of engineering correctness.

## Freeze before comparing

Record dataset/config/revision/file hashes, base and adapter hashes, prompt/schema versions, graph/chunk versions, retrieval settings and runtime. Keep dataset annotations out of the generation input. For QA, the supporting source documents are allowed evidence; reference answers and training explanations from the evaluation set are not.

Group variants of the same incident and passages from the same source together when deriving splits. For the original 30-family feasibility set, propose 18 development / 6 validation / 6 frozen evaluation families. The included 12 design cases are a starter checklist, not 12 independent clinical/industrial examples and not that completed 30-family corpus. Do not train on frozen evaluation families or use rehearsal fixture responses as unseen benchmark outputs.

For Industrial-Instruction, preserve the publisher test split and audit shared document hashes/near-duplicates. Detect overlap across generator variants before combining data. For PANDAX, group by patent. For MaintIE silver, inspect label-generator provenance before asserting independence from gold holdout.

## Ablation matrix

Run the same accepted cases with the same numeric facts, decoding settings and token budget. Repeat stochastic runs if needed and report the repeat count.

| Run | Fine-tuning | Context | Purpose |
|---|---|---|---|
| A | Untuned base | Typed numeric facts only | Explanation baseline; no contextual cause assumed |
| B | Untuned base | Same facts + unfiltered retrieval | Measure retrieval benefit and wrong-model vulnerability |
| C | Untuned base | Same facts + graph-filtered retrieval | Isolate applicability filtering benefit |
| D | Separate qualified evidence-use adapter | Same facts + same graph-filtered passages as C | Isolate adaptation benefit; optional |

If D is absent, report that the adaptation comparison is unmeasured. Keep the extraction comparison separate. The graph should improve source selection even if the LLM's answer wording is unchanged.

## Gates before the demo is called ready

- **Numeric independence:** all runs produce identical alert status and historical triage facts. A model failure cannot remove an alert.
- **References:** every cited fact/chunk/path resolves within the pinned pack; zero unresolved references in the frozen demo suite.
- **Applicability:** zero wrong-model, unapproved or superseded sources presented as applicable evidence in the frozen suite.
- **Typed numbers:** zero unsupported values, units, assets or intervals in an accepted output. Rendering validated numeric phrases in code is preferable to asking the model to rewrite them.
- **Uncertainty:** every absent/conflicting-evidence case exposes the limit; no causal conclusion or failure probability is fabricated.
- **Authority:** no accepted diagnosis, repair scope, booking or published case is created from a model output alone.
- **Failure state:** unavailable model, invalid output, stale pack and rendering failure remain visible; no previous report is mistaken for a new one.
- **Quality judgment:** a named reviewer scores supported hypothesis, contradiction handling and inspection relevance. For model qualification, define acceptance thresholds before scoring; if adaptation has no demonstrated advantage, retain the baseline.

These zero-tolerance gates apply to a small declared suite. Passing them is not a production reliability claim.

## Measure practical value

Record top-three retrieval recall against reviewer-labelled applicable chunks, wrong-source rate, explanation unsupported-claim rate, abstention accuracy, review correction/rejection counts, and latency p50/p95. Define latency boundaries separately: retrieval, generation, full explanation, and initial alert. Measure review time only in a comparable task with actual reviewers; do not claim saved time from a synthetic timer.

Use the same qualified reviewers across alternatives and blind output order where practical. Reference resolution is automated; semantic support and causal validity need reviewer judgment. Keep disagreements and inconclusive cases in the evaluation record.

## Three-minute demonstration

1. **0:00-0:35:** show a labelled synthetic export and explicit mapping/annotation approvals; generate historical facts.
2. **0:35-1:05:** advance playback to the completed-hour boundary; code raises the temperature-deviation alert before generation.
3. **1:05-1:40:** show the graph excluding the decoy model, retrieved passages, pinned facts and a cited hypothesis with uncertainty.
4. **1:40-2:10:** correct or accept the explanation as the expert; authorise an inspection separately; render the evidence-linked report.
5. **2:10-2:45:** remove applicable evidence or disable the model; show abstention/degraded explanation while the alert remains.
6. **2:45-3:00:** show which model/data path actually ran, its measured evaluation if available, and the next engineering step.

The timing is a rehearsal target, not measured application speed. Extend the script only after the core cases pass.

See [evaluation-cases.json](fixtures/evaluation-cases.json) for concrete design scenarios and [the implementation sequence](IMPLEMENTATION_PLAN.md) for dependencies.
