"""State transitions consumed by the connected workspace, without hosted model calls."""
import tempfile
import unittest
from pathlib import Path

from sample_data import sample_items
from ignis_wo.workflow.service import Workflow


class WorkspaceStateTests(unittest.TestCase):
    def test_partial_review_and_repeated_expert_decisions_do_not_falsely_complete_stages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow = Workflow(root / "state.sqlite3", root, sample_items())
            state = workflow.create_run("stage regression", "tester", True, "fixture")
            run_id = state["run_id"]
            csv = "WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h)\n" + "\n".join(
                f"WO-{i},PUMP-SYN-01,2025-01-0{i},pump seal leaking,2" for i in (1, 2))
            state = workflow.upload(run_id, state["revision"], "stage.csv", csv)
            state = workflow.confirm_mapping(run_id, state["revision"], state["proposal"]["mapping"], "checked")
            state = workflow.extract(run_id, state["revision"])
            first, second = [record["record_id"] for record in state["records"]]
            state = workflow.review(run_id, state["revision"], first, "accepted", "checked")
            state = workflow.analyze(run_id, state["revision"])
            self.assertEqual(state["stage_status"]["review"], "pending")
            self.assertEqual(len(state["snapshot"]["entries"]), 1)
            state = workflow.review(run_id, state["revision"], second, "rejected", "excluded")
            state = workflow.analyze(run_id, state["revision"])
            self.assertEqual(state["stage_status"]["review"], "succeeded")
            state = workflow.build_context(run_id, state["revision"], "PUMP-SYN-01", "seal", "seal leakage flush")
            pack = state["context"]["pack"]
            claim = {"text": "Seal leakage is described; causation is unresolved.", "citations": [pack["passages"][0]["passage_id"]], "fact_bindings": []}
            draft = {"pack_id": pack["pack_id"], "hypotheses": [claim], "alternatives": [], "uncertainty": "Cause remains unresolved.", "inspection": None, "abstain": False}
            state = workflow.submit_draft(run_id, state["revision"], draft)
            for decision in ("rejected", "inconclusive", "corrected", "accepted"):
                state = workflow.expert_review(run_id, state["revision"], decision, "tester", "test decision", draft if decision == "corrected" else None)
                self.assertEqual(state["stage_status"]["context"], decision)
                if decision in {"rejected", "inconclusive"}:
                    with self.assertRaisesRegex(ValueError, "signoff"):
                        workflow.issue_report(run_id, state["revision"])
            state = workflow.issue_report(run_id, state["revision"])
            report_id = state["latest_report"]["report_id"]
            state = workflow.expert_review(run_id, state["revision"], "rejected", "tester", "finding withdrawn")
            self.assertIsNone(state["latest_report"])
            self.assertIn(report_id, state["report_ids"])
            self.assertIsNotNone(workflow.store.report(report_id))
