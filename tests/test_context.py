import unittest

from ignis_wo.workflow.context import retrieve, validate_draft


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.fact = {"fact_id": "F-a", "snapshot_id": "S-1", "kind": "severity", "scope": {"asset_id": "PUMP-SYN-01", "component": "seal"}, "value": 1, "unit": "severity_points", "status": "computed", "record_ids": ["WO-1"]}
        self.result = retrieve("PUMP-SYN-01", "seal", "seal leakage flush", [self.fact], "S-1")
        self.pack = self.result["pack"]

    def valid_draft(self):
        return {"pack_id": self.pack["pack_id"], "hypotheses": [{"text": "Seal leakage is described, but its cause is unknown.", "citations": [self.pack["passages"][0]["passage_id"]], "fact_bindings": []}], "alternatives": [], "uncertainty": "Causation is unresolved.", "inspection": {"text": "Inspect the seal and flush path.", "citations": [self.pack["passages"][0]["passage_id"]], "fact_bindings": []}, "abstain": False}

    def test_wrong_model_superseded_and_unapproved_documents_are_excluded(self):
        self.assertEqual(self.result["status"], "ready")
        selected = {p["passage_id"] for p in self.pack["passages"]}
        self.assertNotIn("MAN-PUMP-B-v1", selected)
        self.assertNotIn("MAN-PUMP-A-v0", selected)
        self.assertNotIn("CASE-UNREVIEWED-v1", selected)
        excluded = {e["document_id"] for e in self.result["trace"]["excluded"]}
        self.assertTrue({"MAN-PUMP-B-v1", "MAN-PUMP-A-v0", "CASE-UNREVIEWED-v1"} <= excluded)

    def test_unknown_asset_has_no_broad_retrieval(self):
        result = retrieve("UNKNOWN", "seal", "leak", [self.fact], "S-1")
        self.assertEqual(result["status"], "insufficient_applicability")
        self.assertIsNone(result["pack"])

    def test_validator_requires_exact_scoped_fact_bindings_and_rejects_number_prose(self):
        draft = self.valid_draft()
        draft["hypotheses"][0]["text"] = "Seal leakage is the first likely issue."
        self.assertTrue(any("numbers in prose" in error for error in validate_draft(self.pack, draft)))

        draft = self.valid_draft()
        draft["hypotheses"][0]["citations"] = ["invented"]
        self.assertTrue(any("not in the pack" in error for error in validate_draft(self.pack, draft)))

        draft = self.valid_draft()
        draft["hypotheses"][0]["citations"].append("F-a")
        draft["hypotheses"][0]["fact_bindings"] = [{"fact_id": "F-a", "value": 999, "unit": "hours", "scope": {"component": "motor"}, "snapshot_id": "S-old"}]
        self.assertTrue(any("does not exactly match" in error for error in validate_draft(self.pack, draft)))

    def test_non_abstaining_empty_draft_is_rejected(self):
        draft = self.valid_draft()
        draft["hypotheses"] = []
        self.assertTrue(any("requires at least one hypothesis" in error for error in validate_draft(self.pack, draft)))


if __name__ == "__main__":
    unittest.main()
