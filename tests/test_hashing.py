import unittest

from ignis_wo.hashing import canonical_json, content_hash


class HashingTests(unittest.TestCase):
    def test_key_order_does_not_change_the_hash(self):
        self.assertEqual(content_hash({"a": 1, "b": [1, 2]}), content_hash({"b": [1, 2], "a": 1}))

    def test_any_field_change_changes_the_hash(self):
        self.assertNotEqual(content_hash({"a": 1}), content_hash({"a": 2}))

    def test_canonical_json_is_compact_and_sorted(self):
        self.assertEqual(canonical_json({"b": 1.5, "a": "x"}), '{"a":"x","b":1.5}')


if __name__ == "__main__":
    unittest.main()
