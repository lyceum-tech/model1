"""Independent regressions for rule 10: Stream progress and terminal events."""

import json
import unittest

from review_rules import rule_10 as rule

GOOD = {
    "events": [{"turn": 1, "kind": "content", "time_ms": 1}, {"turn": 1, "kind": "done", "time_ms": 2}],
    "idle_limit_ms": 30000,
}


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update(
            {
                "events": [
                    {"turn": 1, "kind": "content", "time_ms": 1},
                    {"turn": 1, "kind": "error", "time_ms": 2},
                    {"turn": 1, "kind": "done", "time_ms": 3},
                ]
            }
        )
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_array_argument_silence_and_content_after_terminal_are_detected(self):
        events = [{"turn": 1, "kind": "content", "time_ms": 1}, {"turn": 1, "kind": "done", "time_ms": 45000}]
        self.assertIs(rule.evaluate_one({**GOOD, "events": events}), False)
