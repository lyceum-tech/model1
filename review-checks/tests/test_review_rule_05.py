"""Independent regressions for rule 5: Normalization before validation."""

import json
import unittest

from review_rules import rule_05 as rule

GOOD = {"forwarded": False, "accepted": False, "status": 400}


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update({"forwarded": True, "accepted": False, "status": 400})
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_normalizing_after_validation_is_a_violation(self):
        self.assertIs(
            rule.evaluate_one(
                {
                    "accepted": True,
                    "forwarded": True,
                    "normalized": 30,
                    "validated": "30",
                    "upstream_value": 30,
                    "ambiguous_aliases": False,
                }
            ),
            False,
        )
