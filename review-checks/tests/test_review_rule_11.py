"""Independent regressions for rule 11: Routing and failover policy."""

import json
import unittest

from review_rules import rule_11 as rule

GOOD = {
    "attempts": [{"destination": "iris", "after_first_output": False}],
    "permitted_destinations": ["iris"],
    "model_known": False,
    "catalogues_complete": False,
    "status": 503,
}


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update({"status": 404})
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_disallowed_provider_and_post_output_retry_are_violations(self):
        attempts = [
            {"destination": "iris", "after_first_output": False},
            {"destination": "outside", "after_first_output": False},
        ]
        self.assertIs(rule.evaluate_one({**GOOD, "attempts": attempts}), False)
        attempts[1] = {"destination": "iris", "after_first_output": True}
        self.assertIs(rule.evaluate_one({**GOOD, "attempts": attempts}), False)
