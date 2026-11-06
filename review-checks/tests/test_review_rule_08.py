"""Independent regressions for rule 8: Regression tests detect the regression."""

import json
import unittest

from review_rules import rule_08 as rule

GOOD = [
    {
        "scenario": "regression",
        "baseline_tests": 1,
        "candidate_tests": 1,
        "baseline_exit": 1,
        "candidate_exit": 0,
        "baseline_failure_kind": "assertion",
        "behavior_assertions": 1,
    },
    {"scenario": "control", "baseline_tests": 1, "candidate_tests": 1, "baseline_exit": 0, "candidate_exit": 0},
]


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = json.loads(json.dumps(GOOD))
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update({"candidate_exit": 1})
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = json.loads(json.dumps(GOOD))
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_compile_failure_and_empty_discovery_are_not_regression_proof(self):
        fact = GOOD[0]
        self.assertIsNone(rule.evaluate_one({**fact, "baseline_failure_kind": "compile"}))
        self.assertIsNone(rule.evaluate_one({**fact, "candidate_tests": 0}))
