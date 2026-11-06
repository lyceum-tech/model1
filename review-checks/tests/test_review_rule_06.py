"""Independent regressions for rule 6: Prices and measurable usage."""

import json
import unittest

from review_rules import rule_06 as rule

GOOD = {
    "vendor_called": True,
    "served": True,
    "price_key": "image:2K",
    "available_prices": ["image:2K"],
    "forwarded_dimension": "2K",
    "priced_dimension": "2K",
    "quantity": 1,
    "usage_recorded": True,
    "accounting_failure_visible": False,
}


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update({"price_key": "image:1024x1024"})
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_served_unmeasurable_work_cannot_disappear_silently(self):
        fact = {**GOOD, "quantity": 0, "usage_recorded": False}
        self.assertIs(rule.evaluate_one(fact), False)
        self.assertIs(rule.evaluate_one({**fact, "accounting_failure_visible": True}), True)
