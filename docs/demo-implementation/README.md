# IGNIS bounded demo implementation pack

Prepared 14 October 2026 for the team discussion under [UniverseScripts' PR #14](https://github.com/khanhtuongnakitomo/IGNIS/pull/14).

[Posted PR comment](https://github.com/khanhtuongnakitomo/IGNIS/pull/14#issuecomment-6161627651).

**Recommended direction:** keep the deterministic work-order pipeline, add a small graph to select applicable evidence, retrieve a few passages, and let a language model propose a cited explanation. Code owns numeric alerts and priorities; people own diagnosis confirmation and maintenance approval.

This is a historical implementation guide and illustrative fixture pack prepared on 14 October. The fixtures are synthetic, unreviewed design examples, and no dataset has been admitted to a training run. The pack is now versioned with the backend work. For current runnable interfaces and limitations, use the [API contract](../API_CONTRACT.md); these earlier illustrative schemas are not the runtime contract.

## Read in this order

1. [Dataset research](DATASET_RESEARCH.md): what each source can teach, what it cannot, and the recommendation.
2. [Implementation plan](IMPLEMENTATION_PLAN.md): scope, extension points, sequence and acceptance gates.
3. [Evaluation plan](EVALUATION_PLAN.md): compare alternatives and demonstrate failure behavior.
4. [Source receipts](sources.json): checked revisions, file identities and primary-source links.
5. [Context fixture](fixtures/demo-context.json): synthetic graph, documents, measurements and facts.
6. [Reasoning example](fixtures/reasoning-example.json): proposed model output contract and illustrative response.
7. [Evaluation cases](fixtures/evaluation-cases.json): scenario transformations and expected behavior.
8. [PR comment](PR14_COMMENT.md): the exact prepared text for the discussion.

References to PR #14 and `ignis_wo/` below describe the research snapshot at commit `00ad51d14f8be5cd754e524343f4280cb8cc7fba`. The deterministic baseline was subsequently merged through PR #15 and extended by the current backend mission. Follow [the confirmed three-loop direction](../PROPOSED_SYSTEM_WORKFLOW.md); these historical proposals do not replace the current API contract.

## Team decision

Agree on the bounded scope, allocate the implementation responsibilities, and choose a model/runtime only after a structured-output smoke test. An explanation adapter can remain prompted for the first demo. Extraction fine-tuning is a separate measurable deliverable; explanation fine-tuning is optional until its dataset and evaluation qualify it.
