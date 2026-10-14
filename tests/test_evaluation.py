import unittest

from sample_data import sample_adapter, sample_items

from ignis_wo.evaluation.maintie import split_items
from ignis_wo.evaluation.scorer import score_items


class SplitTests(unittest.TestCase):
    def test_positional_split_matches_upstream_arithmetic(self):
        splits = split_items(list(range(1076)))
        self.assertEqual([len(splits[name]) for name in ("train", "dev", "test")], [860, 108, 108])
        self.assertEqual(splits["test"][0], 968)

    def test_split_is_deterministic(self):
        items = list(range(50))
        self.assertEqual(split_items(items), split_items(items))


class ScorerTests(unittest.TestCase):
    def test_identical_predictions_score_one(self):
        result = score_items(sample_items(), sample_adapter())
        self.assertEqual(result["entities"]["f1"], 1.0)
        self.assertEqual(result["relations"]["f1"], 1.0)
        self.assertEqual(result["schema_invalid"], 0)

    def test_perturbed_predictions_match_hand_computed_scores(self):
        result = score_items(sample_items(), sample_adapter(), perturbed=True)
        # Items 0, 3 and 6 get one wrong entity type: 3 of 21 entities wrong.
        self.assertEqual(result["entities"]["correct"], 18)
        self.assertEqual(result["entities"]["f1"], round(18 / 21, 4))
        # Items 0 and 4 lose a relation, but item 4 has none: 1 of 10 relations dropped.
        self.assertEqual(result["relations"]["predicted"], 9)
        self.assertEqual(result["relations"]["recall"], 0.9)
        self.assertEqual(result["relations"]["precision"], 1.0)

    def test_depth_collapses_entity_types(self):
        result = score_items(sample_items(), sample_adapter(), depth=1, perturbed=True)
        self.assertEqual(result["entity_type_depth"], 1)
        self.assertLess(result["entities"]["f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
