# Technical review of the synthetic explanation scenarios

This is a code/definition review of Yoshio's 20 frozen cases. It is not Tuong's expert approval, a blind semantic rating, or new measured model performance. Expected labels and the original scenario lock remain unchanged. Run `scripts/audit_explanation_scenarios.py` to reproduce structural checks without model calls.

| Cases | Interpretation and review requirement |
| --- | --- |
| S01, S11, S13 | Relevant guidance can support a cautious inspection proposal. It does not establish the current asset's root cause. |
| S02, S14 | Both passages describe plausible alternatives. A draft must retain the alternatives and uncertainty rather than choose a cause solely from historical cases. |
| S03, S15 | These passages establish an observation and explicit missing investigation. “Support” may describe that observation, but must not be interpreted as causal diagnostic accuracy. Confirm that the human rubric makes this distinction. |
| S04, S16 | Quantity/unit traps are synthetic fixtures. Their facts do not conform fully to the runtime FactRow contract; they must not be advertised as validated runtime sensor/KPI measurements. Prose quantities remain prohibited. |
| S05, S12 | Retrieved text overlaps lexically with the query but supplies no causal support. Abstention is appropriate; non-empty retrieval is insufficient evidence. |
| S06, S17 | Wrong-model documents must be excluded before drafting. Facts may remain visible independently of context. |
| S07 | The applicable passage explicitly mentions another model's inapplicable procedure. Metadata filtering alone cannot resolve this; the draft and human rating must honor the negation and never recommend that procedure. |
| S08, S18 | The passages describe different historical situations, not necessarily contradictory facts about the current asset. Require competing explanations/uncertainty. Consider a genuinely conflicting current-asset case in a future dataset revision. |
| S09, S19 | Superseded or unreviewed-only evidence must not support a draft. Label synthetic approval metadata clearly. |
| S10, S20 | Lexically matching distractors are intentionally retrieved. Human ratings must check semantic support, including any distractor citation; citation presence alone is insufficient. |

## Structural limitations

The scenario facts are ad-hoc dictionaries, not validated runtime FactRow objects. For example, `work_orders` differs from the runtime `records` unit and required provenance/configuration fields may be absent. The audit lists precise fields per case. This does not retroactively erase the historical comparison, but limits what it proves about the deployed workflow.

The corpus marks synthetic items as approved to exercise filtering while stating that the expected answers await review. Those labels do not represent real expert approval. Keep the entire benchmark labelled synthetic/preliminary.

## Identifier policy and further evaluation

Live inference now uses the versioned v3 prompt, which keeps v2's identifier rule: write “the pump” or “the applicable manual” in prose; put exact IDs only in citations/fact slots. The no-digits validator is unchanged. Recorded answers replay under the prompt they were recorded with and are never relabelled. Measured v2 and v3 dev results are in [BENCHMARKS.md](../../BENCHMARKS.md#v2-against-v3-and-the-default).

The held-out labels have now been inspected and must not be used as an untouched final set for prompt tuning. Preserve the published v1 results. Evaluate v2 on dev/new reviewed cases first; any future final claim needs a new untouched hold-out and blind human semantic ratings.

Before final approval, a human should review every expected outcome, decide how observational support differs from causal support, and complete the blind rating sheet. Do not fill that sheet with model-generated ratings presented as human judgments.
