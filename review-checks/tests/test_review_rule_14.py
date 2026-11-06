"""Independent regressions for rule 14: Secret rotation and reconciliation."""

import json
import unittest

from review_rules import rule_14 as rule

GOOD = {
    "active_key_ids": ["new", "old"],
    "issued_key_id": "new",
    "expected_issuing_key_id": "new",
    "required_blob_ids": ["old-blob"],
    "readable_blob_ids": ["old-blob"],
    "disabled_key_ids": [],
    "after_reconcile_key_ids": ["new", "old"],
}


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update({"after_reconcile_key_ids": ["old"]})
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_rotation_preserves_old_blobs_and_does_not_reenable_disabled_keys(self):
        self.assertIs(rule.evaluate_one({**GOOD, "readable_blob_ids": []}), False)
        self.assertIs(rule.evaluate_one({**GOOD, "disabled_key_ids": ["old"]}), False)
