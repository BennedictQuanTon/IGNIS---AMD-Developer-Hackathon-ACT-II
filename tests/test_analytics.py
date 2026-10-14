import tempfile
import unittest
from pathlib import Path

from sample_data import sample_snapshot

from ignis_wo.analytics.explain import build_explanations, validate_explanation
from ignis_wo.analytics.facts import compute_facts
from ignis_wo.analytics.triage import band_for, severity_for
from ignis_wo.contracts import ComponentCriticality

PUMP_RATING = ComponentCriticality(component="pump", value=10, reason="single duty pump", set_by="supervisor")


def triage_values(facts) -> dict[str, tuple]:
    values = {}
    for fact in facts:
        if fact.kind in ("severity", "recurrence", "criticality", "triage_score"):
            values.setdefault(fact.scope["component"], {})[fact.kind] = fact.value
    return {
        component: (kinds["severity"], kinds["recurrence"], kinds["criticality"], kinds["triage_score"])
        for component, kinds in values.items()
    }


class SeverityAndBandTests(unittest.TestCase):
    def test_longest_class_path_wins(self):
        self.assertEqual(severity_for("State/UndesirableState/FailedState"), 3)
        self.assertEqual(severity_for("State/UndesirableState/DegradedState"), 2)
        self.assertEqual(severity_for("State/UndesirableState"), 1)
        self.assertEqual(severity_for("Property/UndesirableProperty"), 1)
        self.assertEqual(severity_for("State/DesirableState"), 0)

    def test_band_boundaries(self):
        expected = {30: "High", 29: "Medium", 10: "Medium", 9: "Low", 1: "Low", 0: "No fault recorded"}
        for score, band in expected.items():
            self.assertEqual(band_for(score), band, score)


class FactTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_hand_computed_triage(self):
        facts = compute_facts(sample_snapshot(self.path))
        values = triage_values(facts)
        self.assertEqual(values["hose"], (3, 4, 1, 12))
        self.assertEqual(values["pump"], (1, 3, 1, 3))
        self.assertEqual(values["motor"], (3, 1, 1, 3))
        self.assertEqual(values["conveyor belt"], (0, 1, 1, 0))

    def test_criticality_changes_score_and_snapshot(self):
        plain = sample_snapshot(self.path)
        rated = sample_snapshot(self.path, [PUMP_RATING])
        self.assertNotEqual(plain.snapshot_id, rated.snapshot_id)
        self.assertEqual(triage_values(compute_facts(rated))["pump"], (1, 3, 10, 30))

    def test_snapshot_is_deterministic(self):
        first = sample_snapshot(self.path)
        second = sample_snapshot(self.path)
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        self.assertEqual(compute_facts(first), compute_facts(second))

    def test_missing_kpi_fields_are_not_computed(self):
        facts = compute_facts(sample_snapshot(self.path))
        kpis = {fact.scope["kpi"]: fact for fact in facts if fact.kind == "kpi"}
        self.assertEqual(kpis["total_downtime"].value, 12.0)
        self.assertEqual(kpis["mean_time_to_repair"].status, "not_computed")
        self.assertIsNone(kpis["mean_time_to_repair"].value)


class ExplanationTests(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as directory:
            self.snapshot = sample_snapshot(Path(directory), [PUMP_RATING])
        self.facts = compute_facts(self.snapshot)
        self.explanations = build_explanations(self.snapshot, self.facts, "fixture", synthetic=True)

    def test_built_explanations_validate_and_sort_by_priority(self):
        for explanation in self.explanations:
            self.assertEqual(validate_explanation(explanation, self.facts), [])
        self.assertEqual(self.explanations[0].component, "pump")
        self.assertEqual(self.explanations[0].band, "High")

    def test_dominant_fault_and_caveats(self):
        hose = next(explanation for explanation in self.explanations if explanation.component == "hose")
        self.assertEqual(hose.dominant_fault_class, "State/UndesirableState/FailedState")
        self.assertIn("UNATTRIBUTED_FAULTS", hose.caveats)
        self.assertIn("CRITICALITY_DEFAULT", hose.caveats)
        self.assertIn("FIXTURE_MODE", hose.caveats)

    def test_invented_fact_id_is_rejected(self):
        forged = self.explanations[0].model_copy(update={"severity_fact_id": "F-invented00"})
        self.assertTrue(validate_explanation(forged, self.facts))

    def test_wrong_band_is_rejected(self):
        forged = self.explanations[0].model_copy(update={"band": "Low"})
        errors = validate_explanation(forged, self.facts)
        self.assertTrue(any("band" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
