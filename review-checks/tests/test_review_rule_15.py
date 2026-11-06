"""Independent regressions for rule 15: Historical billing correctness."""

import json
import unittest

from review_rules import rule_15 as rule

GOOD = [
    {
        "scenario": "effective-date",
        "price_at": "2026-01-01T12:00:00+00:00",
        "prices": [
            {"valid_from": "2026-01-01T00:00:00+00:00", "price": "1"},
            {"valid_from": "2026-01-02T00:00:00+00:00", "price": "2"},
        ],
        "amount": "1",
        "quantity": "1",
    },
    {"scenario": "historical-update", "rejected": True, "rows_before": ["price1"], "rows_after": ["price1"]},
    {"scenario": "historical-delete", "rejected": True, "rows_before": ["price1"], "rows_after": ["price1"]},
    {"scenario": "rounding", "ending_balance": "-0.01", "lines": [{"kind": "balance", "amount": "0.01"}]},
    {"scenario": "preexisting-price", "migration_succeeded": True, "rows_preserved": True},
]


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = json.loads(json.dumps(GOOD))
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update({"amount": "2"})
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = json.loads(json.dumps(GOOD))
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_small_positive_rounding_remainder_is_not_labelled_credit(self):
        fact = {"scenario": "rounding", "ending_balance": "-0.01", "lines": [{"kind": "credit", "amount": "0.01"}]}
        self.assertIs(rule.evaluate_one(fact), False)
