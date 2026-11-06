"""API compatibility checks must detect breaking contracts without inventing proof."""

import unittest

from review_rules import rule_04 as rule


class APIContractTest(unittest.TestCase):
    def test_removed_operation_and_new_required_parameter_are_breaking(self):
        original = {"paths": {"/models": {"get": {"parameters": []}}}}
        self.assertFalse(rule.compatible(original, {"paths": {}}))
        changed = {"paths": {"/models": {"get": {"parameters": [{"in": "query", "name": "org", "required": True}]}}}}
        self.assertFalse(rule.compatible(original, changed))
        self.assertTrue(rule.compatible(original, original))

    def test_missing_observations_are_yellow_and_bad_sdk_status_is_red(self):
        self.assertEqual(rule.evaluate(None)["status"], "yellow")
        facts = [
            {
                "scenario": name,
                "actual_status": 200,
                "contract_status": 200,
                "required_fields": {"id"},
                "response_fields": {"id", "extra"},
            }
            for name in rule.REQUIRED
        ]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0]["actual_status"] = 404
        self.assertEqual(rule.evaluate(facts)["status"], "red")
