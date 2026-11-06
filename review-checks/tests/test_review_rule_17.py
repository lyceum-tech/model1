"""Independent regressions for rule 17: Alerts match emitted signals."""

import json
import unittest

from review_rules import rule_17 as rule

GOOD: list[dict] = [
    {
        "scenario": "positive",
        "emitted_events": [
            {"message": "refused create: org not on allowlist", "severity": "INFO", "labels": ["service"]}
        ],
        "message_regex": "refused (a )?creat(e|ion).*allowlist",
        "accepted_severities": ["INFO", "WARN"],
        "expected_match": True,
        "bounded_labels": ["service"],
    },
    {
        "scenario": "negative",
        "emitted_events": [{"message": "request completed", "severity": "INFO", "labels": ["service"]}],
        "message_regex": "refused.*allowlist",
        "accepted_severities": ["INFO"],
        "expected_match": False,
        "bounded_labels": ["service"],
    },
    {"scenario": "resolution", "resolved": True},
]


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = json.loads(json.dumps(GOOD))
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update({"accepted_severities": ["ERROR"]})
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = json.loads(json.dumps(GOOD))
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_per_replica_labels_and_unresolved_alerts_are_detected(self):
        fact = GOOD[0]
        event = {**fact["emitted_events"][0], "labels": ["service", "replica_id"]}
        self.assertIs(rule.evaluate_one({**fact, "emitted_events": [event]}), False)
        self.assertIs(rule.evaluate_one({"scenario": "resolution", "resolved": False}), False)
