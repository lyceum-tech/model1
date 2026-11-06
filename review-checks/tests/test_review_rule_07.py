"""Independent regressions for rule 7: Private logs and client errors."""

import json
import unittest

from review_rules import rule_07 as rule

GOOD = {"canaries": ["synthetic-private-value"], "captured_logs": "request failed", "client_error": "unreadable source"}


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update({"captured_logs": "Get https://example.invalid/?signature=synthetic-private-value: timeout"})
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_client_response_and_log_are_both_checked_without_echoing_secrets(self):
        facts = [{"scenario": rule.REQUIRED[0], **GOOD, "client_error": "synthetic-private-value"}]
        result = rule.evaluate(facts)
        self.assertEqual(result["status"], "red")
        self.assertNotIn("synthetic-private-value", str(result))
