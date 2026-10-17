import json
import tempfile
import unittest
from pathlib import Path

from sample_data import pdf_bytes, sample_items

from ignis_wo.documents.corpus import load_corpus_snapshot, publish_corpus, read_artifact, review_artifact
from ignis_wo.documents.ingest import ingest_document, write_outputs
from ignis_wo.extraction.adapters import FixtureAdapter
from ignis_wo.extraction.suggest import suggest_all
from ignis_wo.workflow.context import retrieve
from ignis_wo.workflow.service import Workflow

SEAL_TEXT = "For pump PX-100 inspect seal leakage and the flush supply. This does not identify a root cause."
FACT = {"fact_id": "F-a", "snapshot_id": "S-1", "kind": "severity", "scope": {"component": "seal"}, "value": 1,
        "unit": "severity_points", "status": "computed", "record_ids": ["WO-1"]}


class CorpusTestCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def ingested(self, document_id: str, text: str, revision: int = 1) -> Path:
        path = self.root / f"{document_id}-r{revision}.pdf"
        path.write_bytes(pdf_bytes([text]))
        _, _, directory = ingest_document(path, document_id, revision, "native", self.root / "documents")
        return directory

    def approved(self, document_id: str, text: str, asset_model: str = "PX-100", revision: int = 1, **options) -> Path:
        directory = self.ingested(document_id, text, revision)
        review_artifact(directory, "A. Engineer", "checked against the source", asset_model, "seal", **options)
        return directory

    def snapshot(self, directories: list[Path], name: str = "corpus.json") -> tuple[dict, dict]:
        publish_corpus(directories, {"PUMP-SYN-01": "PX-100"}, self.root / name)
        return load_corpus_snapshot(self.root / name)


class ReviewTests(CorpusTestCase):
    def test_reviews_need_a_reviewer_known_passages_and_approved_corrections(self):
        directory = self.ingested("MAN-1", SEAL_TEXT)
        with self.assertRaisesRegex(ValueError, "reviewer"):
            review_artifact(directory, " ", "reason", "PX-100", "seal")
        with self.assertRaisesRegex(ValueError, "unknown passages"):
            review_artifact(directory, "A. Engineer", "reason", "PX-100", "seal", passage_ids=["invented"])
        with self.assertRaisesRegex(ValueError, "not approved"):
            review_artifact(directory, "A. Engineer", "reason", "PX-100", "seal", corrections={"invented": "text"})
        with self.assertRaisesRegex(ValueError, "at least one"):
            review_artifact(directory, "A. Engineer", "reason", "PX-100", "seal", passage_ids=[])

    def test_a_partial_artifact_is_refused_and_raw_chunks_are_never_rewritten(self):
        directory = self.ingested("MAN-1", SEAL_TEXT)
        raw = (directory / "chunks.jsonl").read_text(encoding="utf-8")
        passage_id = json.loads(raw.splitlines()[0])["passage_id"]
        review_artifact(directory, "A. Engineer", "fixed a typo", "PX-100", "seal", corrections={passage_id: "Fixed."})
        self.assertEqual((directory / "chunks.jsonl").read_text(encoding="utf-8"), raw)
        artifact = json.loads((directory / "artifact.json").read_text(encoding="utf-8"))
        artifact.update({"status": "partial", "missing_pages": [1]})
        (directory / "artifact.json").write_text(json.dumps(artifact), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing pages"):
            review_artifact(directory, "A. Engineer", "reason", "PX-100", "seal")


class ReviewedTextTests(CorpusTestCase):
    def test_text_changed_after_review_blocks_publish_and_reingest(self):
        directory = self.approved("MAN-1", SEAL_TEXT)
        artifact, chunks = read_artifact(directory)
        changed = [chunk.model_copy(update={"text": "Replace the seal now."}) for chunk in chunks]
        data = next(directory.glob("original*")).read_bytes()
        with self.assertRaisesRegex(ValueError, "new reading differs"):
            write_outputs(directory, data, artifact, changed)
        lines = [json.dumps(chunk.model_dump(mode="json"), sort_keys=True) for chunk in changed]
        (directory / "chunks.jsonl").write_text("".join(line + "\n" for line in lines), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs from the reviewed text"):
            publish_corpus([directory], {"PUMP-SYN-01": "PX-100"}, self.root / "corpus.json")

    def test_an_identical_reingest_of_a_reviewed_document_is_allowed(self):
        directory = self.approved("MAN-1", SEAL_TEXT)
        artifact, chunks = read_artifact(directory)
        write_outputs(directory, next(directory.glob("original*")).read_bytes(), artifact, chunks)
        self.assertEqual(len(self.snapshot([directory])[0]["documents"]), len(chunks))


class PublishTests(CorpusTestCase):
    def test_only_approved_chunks_with_matching_models_are_published(self):
        seal = self.ingested("MAN-1", SEAL_TEXT)
        passage_id = json.loads((seal / "chunks.jsonl").read_text(encoding="utf-8").splitlines()[0])["passage_id"]
        review_artifact(seal, "A. Engineer", "checked", "PX-100", "seal", corrections={passage_id: "Corrected text."})
        other_model = self.approved("MAN-2", "For pump PX-200 inspect bearings.", asset_model="PX-200")
        corpus, graph = self.snapshot([seal, other_model])
        self.assertEqual(graph["assets"]["PUMP-SYN-01"]["components"], {"seal": ["MAN-1"]})
        item = next(item for item in corpus["documents"] if item["document_id"] == "MAN-1")
        self.assertEqual((item["text"], item["corrected"], item["status"]), ("Corrected text.", True, "approved"))
        self.assertEqual(item["location"], "page 1 / chunk 1")

    def test_repeated_documents_existing_outputs_and_uncovered_assets_are_refused(self):
        first = self.approved("MAN-1", SEAL_TEXT)
        second = self.approved("MAN-1", SEAL_TEXT + " Revised.", revision=2)
        with self.assertRaisesRegex(ValueError, "one revision per document"):
            publish_corpus([first, second], {"PUMP-SYN-01": "PX-100"}, self.root / "a.json")
        with self.assertRaisesRegex(ValueError, "no review covers"):
            publish_corpus([first], {"PUMP-SYN-02": "PX-900"}, self.root / "b.json")
        self.snapshot([first], "c.json")
        with self.assertRaisesRegex(ValueError, "immutable"):
            publish_corpus([first], {"PUMP-SYN-01": "PX-100"}, self.root / "c.json")

    def test_the_corpus_version_depends_only_on_content(self):
        directory = self.approved("MAN-1", SEAL_TEXT)
        first, _ = self.snapshot([directory], "one.json")
        second, _ = self.snapshot([directory], "two.json")
        self.assertEqual(first["corpus_version"], second["corpus_version"])


class SnapshotRetrievalTests(CorpusTestCase):
    def test_reviewed_chunks_are_retrieved_with_their_source_identity(self):
        reviewed = self.approved("MAN-1", SEAL_TEXT, synthetic=True)
        unreviewed_corpus, graph = self.snapshot([reviewed])
        unreviewed = {**unreviewed_corpus["documents"][0], "passage_id": "UNREVIEWED-1", "status": "candidate"}
        corpus = {**unreviewed_corpus, "documents": [*unreviewed_corpus["documents"], unreviewed]}
        result = retrieve("PUMP-SYN-01", "seal", "seal leakage flush", [FACT], "S-1", (corpus, graph))
        passage = result["pack"]["passages"][0]
        self.assertEqual((result["status"], result["corpus_mode"]), ("ready", "reviewed_snapshot"))
        self.assertEqual([p["passage_id"] for p in result["pack"]["passages"]], [passage["passage_id"]])
        self.assertEqual(passage["location"], "page 1 / chunk 1")
        self.assertEqual(len(passage["source_sha256"]), 64)
        self.assertTrue(result["pack"]["synthetic"])
        self.assertIn("candidate", {entry["reason"] for entry in result["trace"]["excluded"]})

    def test_an_unknown_asset_gets_no_broad_retrieval(self):
        sources = self.snapshot([self.approved("MAN-1", SEAL_TEXT)])
        result = retrieve("PUMP-UNKNOWN", "seal", "seal leakage", [FACT], "S-1", sources)
        self.assertEqual((result["status"], result["pack"]), ("insufficient_applicability", None))

    def test_the_fixture_corpus_stays_the_explicit_default(self):
        result = retrieve("PUMP-SYN-01", "seal", "seal leakage flush", [FACT], "S-1")
        self.assertEqual(result["corpus_mode"], "synthetic_fixture")


def stub_extraction_provider(records):
    return suggest_all(records, FixtureAdapter(sample_items(), model_version="stub-v1"))


stub_extraction_provider.model_id = "Stub-Model"
stub_extraction_provider.model_version = "stub-v1"
stub_extraction_provider.scored_configuration = False


class WorkflowCorpusTests(CorpusTestCase):
    def workflow_to_context(self, sources):
        workflow = Workflow(self.root / "state.sqlite3", self.root / "workflow", sample_items(),
                            extraction_provider=stub_extraction_provider, corpus_sources=sources)
        run = workflow.create_run("reviewed corpus", "tester", True, "injected")
        rows = [f"WO-{index},PUMP-SYN-01,2025-01-{index:02d},pump seal leaking,1.0" for index in range(1, 5)]
        csv_text = "WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h)\n" + "\n".join(rows) + "\n"
        state = workflow.upload(run["run_id"], run["revision"], "synthetic.csv", csv_text)
        state = workflow.confirm_mapping(run["run_id"], state["revision"], state["proposal"]["mapping"], "test headers")
        state = workflow.extract(run["run_id"], state["revision"])
        for record in state["records"]:
            state = workflow.review(run["run_id"], state["revision"], record["record_id"], "accepted", "test",
                                    reviewer="tester")
        state = workflow.analyze(run["run_id"], state["revision"], [])
        state = workflow.build_context(run["run_id"], state["revision"], "PUMP-SYN-01", "seal", "seal leakage flush")
        return workflow, state

    def test_a_report_names_the_extraction_model_and_its_evidence_sources(self):
        workflow, state = self.workflow_to_context(self.snapshot([self.approved("MAN-1", SEAL_TEXT, synthetic=True)]))
        pack = state["context"]["pack"]
        passage_id = pack["passages"][0]["passage_id"]
        draft = {"pack_id": pack["pack_id"], "alternatives": [], "uncertainty": "Causation is unresolved.",
                 "hypotheses": [{"text": "Seal leakage is described; its cause is unresolved.", "citations": [passage_id],
                                 "fact_bindings": []}], "inspection": None, "abstain": False}
        state = workflow.submit_draft(state["run_id"], state["revision"], draft)
        state = workflow.expert_review(state["run_id"], state["revision"], "accepted", "A. Engineer", "checked")
        issued = workflow.issue_report(state["run_id"], state["revision"])
        report = issued["latest_report"]
        self.assertEqual(report["extraction_identity"]["model_id"], "Stub-Model")
        self.assertEqual(report["extraction_identity"]["configuration"], "not the scored configuration")
        self.assertEqual(report["corpus_mode"], "reviewed_snapshot")
        self.assertTrue(Path(report["path"]).exists())

    def test_fixture_runs_saved_before_identity_recording_keep_their_fixture_model(self):
        workflow = Workflow(self.root / "state.sqlite3", self.root / "workflow", sample_items())
        identity = workflow.report_extraction_identity({"adapter_mode": "fixture"})
        self.assertEqual((identity["model_id"], identity["model_version"]), ("fixture-gold", "maintie-gold-demo"))
        self.assertEqual(workflow.report_extraction_identity({"adapter_mode": "unavailable"})["model_id"], "unavailable")

    def test_rebuilding_with_another_corpus_gives_a_new_pack_and_clears_the_draft(self):
        first_sources = self.snapshot([self.approved("MAN-1", SEAL_TEXT)], "first.json")
        workflow, state = self.workflow_to_context(first_sources)
        first_pack = state["context"]["pack"]["pack_id"]
        workflow.corpus_sources = self.snapshot([self.approved("MAN-3", SEAL_TEXT + " Check the gland.")], "second.json")
        rebuilt = workflow.build_context(state["run_id"], state["revision"], "PUMP-SYN-01", "seal", "seal leakage flush")
        self.assertNotEqual(rebuilt["context"]["pack"]["pack_id"], first_pack)
        self.assertEqual((rebuilt["draft_result"], rebuilt["expert_reviews"]), (None, []))


if __name__ == "__main__":
    unittest.main()
