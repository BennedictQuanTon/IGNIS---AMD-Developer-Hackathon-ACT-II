import tempfile
import unittest
from pathlib import Path

from sample_data import sample_snapshot

from ignis_wo.analytics.explain import build_explanations
from ignis_wo.analytics.facts import compute_facts
from ignis_wo.contracts import ClaimSlot
from ignis_wo.render.claims import check_claim, check_claims
from ignis_wo.render.templates import build_claims


class ClaimCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory:
            cls.snapshot = sample_snapshot(Path(directory))
        cls.facts = compute_facts(cls.snapshot)
        explanations = build_explanations(cls.snapshot, cls.facts, "fixture", synthetic=True)
        cls.claims = build_claims(cls.snapshot, cls.facts, explanations)
        cls.known = {fact.fact_id: fact for fact in cls.facts}
        cls.triage = next(claim for claim in cls.claims if claim.template_id == "component.triage")

    def check(self, claim) -> list[str]:
        return check_claim(claim, self.known, self.snapshot.snapshot_id)

    def with_template(self, template: str):
        return self.triage.model_copy(update={"template": template, "slots": [], "text": template})

    def test_generated_claims_all_pass(self):
        self.assertEqual(check_claims(self.claims, self.facts, self.snapshot.snapshot_id), {})

    def test_triage_sentence_reads_correctly(self):
        hose = next(claim for claim in self.claims if claim.template_id == "component.triage" and "hose" in claim.text)
        self.assertEqual(hose.text, "hose has triage priority 12 (Medium): severity 3 × recurrence 4 × criticality 1.")

    def test_free_numbers_are_blocked(self):
        for sentence in ["Pump failed 3 times.", "Pump failed three times.", "Pump failed twice.", "Up 5% this year.", "The first failure."]:
            self.assertTrue(self.check(self.with_template(sentence)), sentence)

    def test_prediction_wording_is_blocked(self):
        errors = self.check(self.with_template("{{label:component}} is at high risk."))
        self.assertTrue(any("banned wording" in error for error in errors))

    def test_digits_inside_labels_are_allowed(self):
        claim = self.with_template("Asset {{label:component}} is listed.")
        claim = claim.model_copy(update={"labels": {"component": "HT-101"}, "text": "Asset HT-101 is listed."})
        self.assertEqual(self.check(claim), [])

    def test_fact_for_another_component_is_blocked(self):
        other = next(fact for fact in self.facts if fact.kind == "recurrence" and fact.scope["component"] != "hose")
        hose = next(claim for claim in self.claims if claim.template_id == "component.triage" and "hose" in claim.text)
        slots = [slot.model_copy(update={"fact_id": other.fact_id}) if slot.role == "recurrence" else slot for slot in hose.slots]
        errors = self.check(hose.model_copy(update={"slots": slots}))
        self.assertTrue(any("does not match component" in error for error in errors), errors)

    def test_wrong_kind_or_unit_is_blocked(self):
        severity_slot = next(slot for slot in self.triage.slots if slot.role == "severity")
        wrong = ClaimSlot(role="score", fact_id=severity_slot.fact_id, expected_kind="triage_score", expected_unit="score")
        slots = [wrong if slot.role == "score" else slot for slot in self.triage.slots]
        errors = self.check(self.triage.model_copy(update={"slots": slots}))
        self.assertTrue(any("expected triage_score/score" in error for error in errors), errors)

    def test_fact_from_another_snapshot_is_blocked(self):
        errors = check_claim(self.triage, self.known, "S-another")
        self.assertTrue(any("is not in snapshot" in error for error in errors))

    def test_edited_text_is_blocked(self):
        edited = self.triage.model_copy(update={"text": self.triage.text.replace("triage priority", "priority score of about")})
        errors = self.check(edited)
        self.assertIn("rendered text does not match the bound fact values", errors)


if __name__ == "__main__":
    unittest.main()
