"""Independent regressions for rule 13: Reversible infrastructure transitions."""

import json
import unittest

from review_rules import rule_13 as rule

GOOD = {
    "actual_active_services": ["execlet"],
    "desired_active_services": ["execlet"],
    "resource_owners": {"gpu0": ["execlet"]},
    "workload_succeeded": True,
    "obsolete_services": ["execlet@0"],
    "enabled_services": ["execlet"],
}


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update({"enabled_services": ["execlet", "execlet@0"]})
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_reverse_transition_cannot_leave_two_gpu_owners(self):
        self.assertIs(rule.evaluate_one({**GOOD, "resource_owners": {"gpu0": ["execlet", "execlet@0"]}}), False)
        self.assertIs(rule.evaluate_one({**GOOD, "workload_succeeded": False}), False)
