"""Workflow API contract and persistence behavior, exercised over a real loopback socket."""
import csv
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sample_data import sample_items
from ignis_wo.extraction.adapters import FixtureAdapter
from ignis_wo.workflow.api import handler_for
from ignis_wo.workflow.service import Workflow


class WorkflowApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "state.sqlite3"
        self.items = sample_items()
        self.workflow = Workflow(self.db, self.root / "data", self.items)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(self.workflow))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def call(self, method, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request) as response:
                content = response.read()
                return response.status, content if response.headers.get_content_type() == "application/pdf" else json.loads(content or b"{}")
        except HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    def post(self, path, payload):
        status, value = self.call("POST", path, payload)
        self.assertLess(status, 400, value)
        return value

    def test_complete_reviewed_workflow_survives_restart_and_downloads_report(self):
        base = self.post("/runs", {"name": "pump demo", "operator": "local-reviewer", "synthetic": True, "adapter_mode": "fixture"})
        rid, rev = base["run_id"], base["revision"]
        csv_text = "WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h)\nWO-1,PUMP-SYN-01,2025-01-01,pump seal leaking,2.0\n"
        uploaded = self.post(f"/runs/{rid}/upload", {"expected_revision": rev, "filename": "synthetic.csv", "csv_text": csv_text})
        self.assertEqual(uploaded["revision"], 1)
        stale_status, stale = self.call("POST", f"/runs/{rid}/upload", {"expected_revision": 0, "filename": "stale.csv", "csv_text": "corrupt"})
        self.assertEqual(stale_status, 409)
        self.assertEqual(self.call("GET", f"/runs/{rid}/preview")[1]["row_count"], 1)
        rev = uploaded["revision"]
        mapping = self.post(f"/runs/{rid}/mapping/confirm", {"expected_revision": rev, "mapping": uploaded["proposal"]["mapping"], "reason": "headers checked"})
        run = self.post(f"/runs/{rid}/extraction/start", {"expected_revision": mapping["revision"]})
        record_id = run["records"][0]["record_id"]
        reviewed = self.post(f"/runs/{rid}/records/{record_id}", {"expected_revision": run["revision"], "status": "accepted", "reason": "reviewed against source"})
        reviewed = self.post(f"/runs/{rid}/records/{record_id}", {"expected_revision": reviewed["revision"], "status": "accepted", "reason": "separate reviewer attribution", "reviewer": "line-engineer"})
        analyzed = self.post(f"/runs/{rid}/analyze", {"expected_revision": reviewed["revision"], "criticalities": [{"component": "seal", "value": 3, "reason": "demo critical component", "set_by": "supervisor"}]})
        self.assertEqual(analyzed["snapshot"]["entries"][0]["annotation_id"], self.workflow.get(rid)["snapshot"]["entries"][0]["annotation_id"])
        from ignis_wo.contracts import CanonicalRecord, ExtractionSuggestion
        from ignis_wo.review import apply_decisions
        annotations = apply_decisions([ExtractionSuggestion.model_validate(run["suggestions"][0])], [CanonicalRecord.model_validate(run["records"][0])], analyzed["decisions"], "fallback-operator")
        self.assertEqual(annotations[0].reviewer, "line-engineer")
        self.assertEqual(analyzed["snapshot"]["entries"][0]["annotation_id"], annotations[0].annotation_id)
        crossed = self.post(f"/runs/{rid}/analyze", {"expected_revision": analyzed["revision"], "criticalities": [{"component": "seal", "value": 30, "reason": "demo critical component", "set_by": "supervisor"}]})
        self.assertTrue(any(a["type"] == "high_band_crossing" for a in crossed["alerts"]))
        repeated = self.post(f"/runs/{rid}/analyze", {"expected_revision": crossed["revision"], "criticalities": [{"component": "seal", "value": 30, "reason": "demo critical component", "set_by": "supervisor"}]})
        self.assertEqual(repeated["alerts"], crossed["alerts"])
        context = self.post(f"/runs/{rid}/context", {"expected_revision": repeated["revision"], "asset_id": "PUMP-SYN-01", "component": "seal", "query": "seal leakage flush"})
        pack = context["context"]["pack"]
        self.assertEqual(context["context"]["status"], "ready")
        self.assertNotIn("answer", pack)
        wrong_asset = self.workflow.build_context(rid, context["revision"], "PUMP-SYN-OTHER", "seal", "leakage")
        self.assertEqual(wrong_asset["context"]["status"], "insufficient_applicability")
        context = self.post(f"/runs/{rid}/context", {"expected_revision": wrong_asset["revision"], "asset_id": "PUMP-SYN-01", "component": "seal", "query": "seal leakage flush"})
        pack = context["context"]["pack"]
        claim = {"text": "Seal leakage is recorded; this does not establish a cause.", "citations": [pack["passages"][0]["passage_id"]], "fact_bindings": []}
        draft = {"pack_id": pack["pack_id"], "hypotheses": [claim], "alternatives": [{"text": "Flush flow remains another condition for inspection.", "citations": [pack["passages"][0]["passage_id"]], "fact_bindings": []}], "uncertainty": "Causation is unresolved.", "inspection": {"text": "Check the seal and flush path.", "citations": [pack["passages"][0]["passage_id"]], "fact_bindings": []}, "abstain": False}
        # Continue from latest committed revision after wrong-asset request.
        reviewed_draft = self.post(f"/runs/{rid}/context/draft", {"expected_revision": context["revision"], "draft": draft})
        accepted = self.post(f"/runs/{rid}/expert-review", {"expected_revision": reviewed_draft["revision"], "decision": "accepted", "reviewer": "engineer", "reason": "references checked"})
        issued = self.post(f"/runs/{rid}/reports/issue", {"expected_revision": accepted["revision"]})
        prior_report_id = issued["latest_report"]["report_id"]
        prior_pdf_path = Path(issued["latest_report"]["path"])
        with patch("ignis_wo.workflow.service.build_pdf", side_effect=RuntimeError("render fixture failure")):
            failed_status, failed_report = self.call("POST", f"/runs/{rid}/reports/issue", {"expected_revision": issued["revision"]})
        self.assertEqual(failed_status, 422)
        self.assertEqual(failed_report["error"], "stage_failed")
        self.assertEqual(failed_report["stage"], "report")
        self.assertIn("render fixture failure", failed_report["message"])
        self.assertEqual(failed_report["current_revision"], issued["revision"] + 1)
        failed_state = self.workflow.get(rid)
        self.assertEqual(failed_state["revision"], failed_report["current_revision"])
        self.assertIsNone(failed_state.get("latest_report"))
        self.assertEqual(failed_state["stage_status"]["report"], "failed")
        self.assertTrue(any("render fixture failure" in error for error in failed_state["stage_errors"]))
        self.assertEqual(self.workflow.store.history(rid)[-1]["kind"], "report_render_failed")
        self.assertTrue(prior_pdf_path.exists())
        status, prior_pdf = self.call("GET", f"/runs/{rid}/report/{prior_report_id}")
        self.assertEqual(status, 200)
        self.assertTrue(prior_pdf.startswith(b"%PDF"))
        self.assertEqual(list((self.root / "data" / "outputs" / rid).glob("*.pdf")), [prior_pdf_path])
        issued = self.post(f"/runs/{rid}/reports/issue", {"expected_revision": failed_state["revision"]})
        self.assertEqual(issued["latest_report"]["status"], "issued")
        self.assertFalse(any(error.startswith("report:") for error in issued.get("stage_errors", [])))
        state = Workflow(self.db, self.root / "data", self.items).get(rid)
        self.assertEqual(state["latest_report"]["report_id"], issued["latest_report"]["report_id"])
        status, pdf = self.call("GET", f"/runs/{rid}/report/{issued['latest_report']['report_id']}")
        self.assertEqual(status, 200)
        self.assertTrue(pdf.startswith(b"%PDF"))
        parse_status, parse_failure = self.call("POST", f"/runs/{rid}/upload", {"expected_revision": issued["revision"], "filename": "bad.json", "csv_text": "{"})
        self.assertEqual(parse_status, 422)
        self.assertEqual(parse_failure["run"]["latest_report"], None)
        self.assertEqual(parse_failure["run"]["stage_status"]["report"], "pending")
        self.assertIn(issued["latest_report"]["report_id"], parse_failure["run"]["report_ids"])
        status, preserved_pdf = self.call("GET", f"/runs/{rid}/report/{issued['latest_report']['report_id']}")
        self.assertEqual(status, 200)
        self.assertTrue(preserved_pdf.startswith(b"%PDF"))
        changed = self.post(f"/runs/{rid}/records/{record_id}", {"expected_revision": parse_failure["current_revision"], "status": "accepted", "reason": "new review revision"})
        self.assertIsNone(changed["snapshot"])
        self.assertIsNone(changed["latest_report"])
        self.assertEqual(changed["stage_status"]["facts"], "pending")
        self.assertEqual(changed["stage_status"]["context"], "pending")
        self.assertEqual(changed["stage_status"]["report"], "pending")
        status, old_pdf = self.call("GET", f"/runs/{rid}/report/{issued['latest_report']['report_id']}")
        self.assertEqual(status, 200)
        self.assertTrue(old_pdf.startswith(b"%PDF"))
        reanalyzed = self.post(f"/runs/{rid}/analyze", {"expected_revision": changed["revision"]})
        blocked, message = self.call("POST", f"/runs/{rid}/reports/issue", {"expected_revision": reanalyzed["revision"]})
        self.assertEqual(blocked, 422)
        self.assertIn("signoff", message["message"])

    def test_upload_parser_failure_is_persisted_and_retry_uses_returned_revision(self):
        created = self.post("/runs", {"name": "parse failure", "operator": "local-reviewer", "synthetic": True})
        rid = created["run_id"]
        status, failure = self.call("POST", f"/runs/{rid}/upload", {"expected_revision": created["revision"], "filename": "bad.json", "csv_text": "{"})
        self.assertEqual(status, 422)
        self.assertEqual(failure["error"], "stage_failed")
        self.assertEqual(failure["stage"], "upload")
        state = failure["run"]
        self.assertEqual(state["revision"], failure["current_revision"])
        self.assertEqual(state["stage_status"]["upload"], "failed")
        self.assertTrue(any("upload:" in error for error in state["stage_errors"]))
        self.assertEqual(self.workflow.store.history(rid)[-1]["kind"], "upload_parse_failed")
        retried = self.post(f"/runs/{rid}/upload", {"expected_revision": state["revision"], "filename": "good.json", "content_base64": "W3siZGVzY3JpcHRpb24iOiJwdW1wIHNlYWwgbGVha2luZyJ9XQ=="})
        self.assertEqual(retried["stage_status"]["upload"], "succeeded")

    def test_manual_correction_and_facts_only_signoff_work_without_provider(self):
        workflow = Workflow(self.db, self.root / "manual", self.items)
        created = workflow.create_run("manual fallback", "local-reviewer", True, "unavailable")
        rid = created["run_id"]
        csv_text = "WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h)\nWO-1,PUMP-SYN-01,2025-01-01,pump seal leaking,2.0\n"
        uploaded = workflow.upload(rid, 0, "source.csv", csv_text)
        mapped = workflow.confirm_mapping(rid, uploaded["revision"], uploaded["proposal"]["mapping"], "confirmed")
        unavailable = workflow.extract(rid, mapped["revision"])
        output = FixtureAdapter(self.items).extract("pump seal leaking")
        corrected = workflow.review(rid, unavailable["revision"], unavailable["records"][0]["record_id"], "corrected", "manual correction after provider unavailable", output)
        self.assertEqual(corrected["decisions"][unavailable["records"][0]["record_id"]]["revision"], 1)
        analyzed = workflow.analyze(rid, corrected["revision"])
        no_context = workflow.build_context(rid, analyzed["revision"], "PUMP-SYN-01", "seal", "leak")
        self.assertEqual(no_context["context"]["status"], "ready")
        model_unavailable = workflow.generate_context_draft(rid, no_context["revision"])
        self.assertEqual(model_unavailable["draft_result"]["status"], "unavailable")
        approved = workflow.expert_review(rid, model_unavailable["revision"], "facts_only_approved", "engineer", "explanation provider unavailable; facts reviewed")
        issued = workflow.issue_report(rid, approved["revision"])
        self.assertEqual(issued["latest_report"]["status"], "issued")
        self.assertEqual(workflow.get(rid)["draft_result"]["explanation_mode"], "unavailable")

    def test_analysis_rejects_cross_asset_history(self):
        workflow = Workflow(self.db, self.root / "multi", self.items)
        created = workflow.create_run("multi asset", "reviewer", True, "fixture")
        rid = created["run_id"]
        source = "WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h)\nWO-1,PUMP-SYN-01,2025-01-01,pump seal leaking,1\nWO-2,PUMP-SYN-02,2025-01-02,replace hose burst,2\n"
        uploaded = workflow.upload(rid, 0, "pump.csv", source)
        mapped = workflow.confirm_mapping(rid, uploaded["revision"], uploaded["proposal"]["mapping"], "confirmed")
        extracted = workflow.extract(rid, mapped["revision"])
        revision = extracted["revision"]
        for record in extracted["records"]:
            reviewed = workflow.review(rid, revision, record["record_id"], "accepted", "reviewed")
            revision = reviewed["revision"]
        with self.assertRaisesRegex(ValueError, "cannot mix asset identities"):
            workflow.analyze(rid, revision)

    def test_upstream_review_invalidates_signoff_and_analysis_compares_previous_snapshot(self):
        start = self.post("/runs", {"operator": "reviewer", "synthetic": True, "adapter_mode": "fixture"})
        rid = start["run_id"]
        source = "WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h)\nWO-1,PUMP-SYN-01,2025-01-01,replace hose burst,1\nWO-2,PUMP-SYN-01,2025-01-02,pump seal leaking,2\n"
        uploaded = self.post(f"/runs/{rid}/upload", {"expected_revision": 0, "filename": "pump.csv", "csv_text": source})
        mapped = self.post(f"/runs/{rid}/mapping/confirm", {"expected_revision": uploaded["revision"], "mapping": uploaded["proposal"]["mapping"], "reason": "confirmed"})
        extracted = self.post(f"/runs/{rid}/extraction/start", {"expected_revision": mapped["revision"]})
        failed_row, ordinary = extracted["records"]
        first_review = self.post(f"/runs/{rid}/records/{failed_row['record_id']}", {"expected_revision": extracted["revision"], "status": "accepted", "reason": "reviewed"})
        second_review = self.post(f"/runs/{rid}/records/{ordinary['record_id']}", {"expected_revision": first_review["revision"], "status": "accepted", "reason": "reviewed"})
        first = self.post(f"/runs/{rid}/analyze", {"expected_revision": second_review["revision"], "criticalities": [{"component": "hose", "value": 3, "reason": "critical", "set_by": "supervisor"}]})
        failed_alerts = [a for a in first["alerts"] if a["type"] == "critical_component_failed_state"]
        self.assertEqual(len(failed_alerts), 1)
        second_same = self.post(f"/runs/{rid}/analyze", {"expected_revision": first["revision"], "criticalities": [{"component": "hose", "value": 3, "reason": "critical", "set_by": "supervisor"}]})
        self.assertEqual(second_same["alerts"], first["alerts"])
        corrected = self.post(f"/runs/{rid}/records/{failed_row['record_id']}", {"expected_revision": second_same["revision"], "status": "rejected", "reason": "record excluded after audit"})
        self.assertIsNone(corrected["snapshot"])
        self.assertEqual(corrected["expert_reviews"], [])
        self.assertEqual(corrected["stage_status"]["facts"], "pending")
        self.assertEqual(corrected["stage_status"]["alerts"], "pending")
        self.assertEqual(corrected["stage_status"]["report"], "pending")
        revised = self.post(f"/runs/{rid}/analyze", {"expected_revision": corrected["revision"], "criticalities": [{"component": "hose", "value": 3, "reason": "critical", "set_by": "supervisor"}]})
        self.assertTrue(any(a["type"] == "finding_retracted" for a in revised["alerts"]))

    def test_reuploaded_different_asset_starts_fresh_alert_baseline(self):
        workflow = Workflow(self.db, self.root / "asset-boundary", self.items)
        created = workflow.create_run("asset boundary", "reviewer", True, "fixture")
        rid, revision = created["run_id"], created["revision"]

        def load_asset(asset):
            nonlocal revision
            source = "WO #,Equipment ID,Reported Date,Work Order Description,Downtime (h)\n" + "".join(
                f"WO-1,{asset},2025-01-{day:02d},replace hose burst,1\n" for day in range(1, 13)
            )
            uploaded = workflow.upload(rid, revision, "pump.csv", source)
            mapped = workflow.confirm_mapping(rid, uploaded["revision"], uploaded["proposal"]["mapping"], "verified source columns")
            extracted = workflow.extract(rid, mapped["revision"])
            reviewed = extracted
            for record in extracted["records"]:
                reviewed = workflow.review(rid, reviewed["revision"], record["record_id"], "accepted", "reviewed")
            analyzed = workflow.analyze(rid, reviewed["revision"], [{"component": "hose", "value": 3, "reason": "critical", "set_by": "supervisor"}])
            revision = analyzed["revision"]
            return analyzed

        first = load_asset("PUMP-SYN-01")
        self.assertTrue(any(a["type"] == "critical_component_failed_state" for a in first["alerts"]))
        second = load_asset("PUMP-SYN-02")
        self.assertTrue(any(a["type"] == "critical_component_failed_state" for a in second["alerts"]))
        self.assertFalse(any(a["type"] in {"finding_retracted", "high_band_crossing"} for a in second["alerts"]))
        self.assertTrue(any(a["type"] == "initial_high_notice" for a in second["alerts"]))


if __name__ == "__main__":
    unittest.main()
