# Dataset choices for the IGNIS demo

**Recommendation:** retain MaintIE gold for extraction. Pilot Industrial-Instruction for learning to use retrieved technical evidence, subject to its stated data-use terms and a label-quality audit. Use AssetOpsBench to design maintenance evaluations and PANDAX as an optional relationship/explanation experiment. Create a small team-reviewed pump evidence set to evaluate the actual IGNIS output contract.

Verified on 14 October 2026. File identities and inspection evidence are recorded in [sources.json](sources.json). These recommendations are task-fit judgments, not measured IGNIS results.

## Compare by the job we need

| Source | Verified content | Best role | Main limit | Recommendation |
|---|---|---|---|---|
| [MaintIE gold](https://github.com/nlp-tlp/maintie) | 1,076 fine-grained maintenance texts with entity spans and relations; PR split 860/108/108 | Component/fault/action extraction | Does not contain telemetry-to-diagnosis or cited reasoning answers | Keep as the extraction baseline |
| [Industrial-Instruction](https://huggingface.co/datasets/Parssky/industrial-instruction-dataset) | Current `pana_qa_v1`: 12,557 train / 1,000 test; `pana_qa_claude_v1`: 25,252 train / 1,000 test. Fields: question, answer choices, supporting documents | Evidence-conditioned technical QA; noisy retrieval behavior | Synthetic multiple-choice labels; largely Panasonic technical documentation, not pump incidents; CC BY-NC 4.0 | Strongest new candidate for an evidence-use pilot; not direct maintenance diagnosis training |
| [AssetOpsBench](https://huggingface.co/datasets/ibm-research/AssetOpsBench) | Scenario prompts and expected response characteristics; includes compressor, hydraulic-pump and failure-mode/sensor configurations | Maintenance task selection, graph applicability and evaluation design | Expectations are not complete expert-approved answer trajectories; some cases need the accompanying tool/data environment | Prefer evaluation first; only independently verified adaptations become training data |
| [PANDAX v1](https://zenodo.org/records/14510798) | 1,860 question/answer/explanation triples organised by 20 patent documents, including part-of, function and parameter questions | Relationship interpretation and evidence explanations | Patent domain differs from operating equipment; explanations have mixed model/human origins | Optional small reviewed subset; split by patent, not individual question |
| [MetroPT-3](https://archive.ics.uci.edu/dataset/791/metropt+3+dataset) | Compressor sensor time series, accompanying failure-report information | Later numeric replay/condition evaluation | Not language-model instruction data; not the same asset as our synthetic pump | Defer from the first demo |

### 1. Industrial-Instruction: closest match to context-aware language behavior

The current release has renamed configs to `pana_*`; older search results use `panasonic_*`. Pin revision `894b5104d5cdf40cb55eec2fe0ba704745f539f0`. Inspect actual files rather than copying an older loading example. The author [repository](https://github.com/parssky/industrial-instruction) and [paper](https://arxiv.org/abs/2608.22817) explain the retrieval-grounded task.

Released answer labels are sets of choices, not reviewed explanations or citation bindings. Use them to train/evaluate that task as-is, or manually curate supported answers into the IGNIS contract. Do not invent rationales from answer keys and call them expert labels. Our first inspected training row includes numerical choices not all explicitly supported by its provided passage; label grounding needs review before use.

For a pilot, choose one generator/config rather than mixing both variants, which may share documents or question families. Use up to 1,000 training examples as a resource-bounded experiment after screening. Preserve the publisher test split; derive development groups from training only, grouping shared document chunks and question variants. The released schema lacks stable document IDs, so hash normalized passages and audit connected overlap across splits. Report any limitation of the published split rather than claiming document-independent generalisation.

The dataset card states CC BY-NC 4.0 and requires following source-document terms. That is a material condition for selection; a public download is not a blanket permission for product use. If intended hackathon/training use is unresolved, use our original synthetic fixtures for the demo and leave this candidate out of training until resolved.

### 2. AssetOpsBench: useful industrial scenarios, not turnkey reasoning supervision

Pin the inspected Hugging Face revision `5e25bb7f2cd37fb68b9a9e1f99d170ca5be7ce17`. The card states Apache 2.0. The actual config spelling is `hydrolic_pump`; the corresponding file is `hydrolicpump_utterance.jsonl`.

Full small-file inspection found 15 compressor scenarios, 17 hydraulic-pump scenarios and 88 failure-mode/sensor-mapping scenarios in the selected files. Its `characteristic_form` supplies expected content or a rubric, sometimes requiring tools, asset metadata and external data. Use selected questions to design supported/unsupported-evidence tests. A scenario labelled `train` by the host is not automatically a gold supervised-training example. Audit question/rubric consistency, asset identity and dates. Renaming an industrial asset does not make its measurements belong to our pump. Keep `failure_event`, hints and answer rubrics out of the inference input when they reveal the target outcome.

### 3. PANDAX: a small relationship and explanation supplement

Zenodo API metadata identifies CC BY 4.0. The JSON groups examples by patent, question category and example ID, with fields including `Q`, `A`, `E`, `E_source` and `vote_A_count`. Full-file inspection found 346 entries marked `human_eval` and 1,514 with named model origins. That field is provenance, not our independent validation. Majority votes and a model-generated explanation are not equivalent to engineering confirmation.

Reconstruct evidence from the corresponding patent before converting an example to cited output. Do not treat patent possibilities as operating instructions or causal proof. Keep every patent and its paraphrases in one split. Use a small reviewed subset only if it adds value beyond the main pilot.

## Extraction expansion and alternatives

[MaintIE silver](https://github.com/nlp-tlp/maintie#3-corpora) contains 7,000 coarse-labelled texts. It is a secondary extraction experiment, not a new reasoning dataset. Its taxonomy differs from gold and its labels were model-produced then reviewed. Check teacher training provenance and overlap before evaluating on the gold holdout; do not assume the silver corpus is independent of that test set.

[INGENZI_DatasetV1](https://huggingface.co/datasets/BernesLy/INGENZI_DatasetV1) has 10,294 question/answer/context pairs about MRI and ultrasound equipment. Its card states CC BY-NC 4.0 and describes synthetic generation with review during filtering. Its format is closer to grounded answers, but the equipment mismatch makes it a lower-priority choice for the pump demo.

TechQA is an IT-support adaptation dataset, and FaultGPT is oriented toward multimodal vibration diagnosis. They do not fit the first text/evidence demo as closely; avoid broadening the stack just to include them.

## Proposed training and evidence lanes

1. **Extraction:** MaintIE gold training split -> exact span/relation JSON; compare untuned and adapted models on the same dev set. Keep test locked.
2. **Evidence-conditioned QA pilot:** screened Industrial-Instruction training rows -> original multiple-choice task. This tests an adaptation hypothesis, not pump diagnosis competence.
3. **IGNIS explanation:** first use an explicitly configured prompted model. Build a separate original synthetic, team-reviewed set of fact/passages -> cited hypothesis/uncertainty/abstention records. Do not claim fine-tuning gains from a small rehearsal set.
4. **Retrieval:** approved manual chunks and reviewed cases remain external evidence. Updating them is an index/data change, not retraining.
5. **Numeric condition assessment:** use authored synthetic inputs and explicit rules for the demo; do not train an LLM on sensor rows as a substitute for a validated numeric model.

No public source inspected supplies a complete, expert-validated pump sensor -> applicability graph -> cited hypothesis -> approved maintenance outcome chain. Building and reviewing that small bridge is still our work. Begin with 30 independent scenario families: 18 development, 6 validation and 6 frozen evaluation families. That is a feasibility/rehearsal set, not a robust efficacy benchmark or sufficient evidence for a production reasoning release.
