"""Independent regressions for rule 9: Streaming response parity."""

import json
import unittest

from review_rules import rule_09 as rule

GOOD = {
    "assembled_stream": {
        "text": "answer",
        "model": "public-model",
        "usage": {"input": 7, "output": 2},
        "finish_reason": "stop",
    },
    "complete_response": {
        "text": "answer",
        "model": "public-model",
        "usage": {"input": 7, "output": 2},
        "finish_reason": "stop",
    },
}


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update(
            {
                "assembled_stream": {
                    "text": "Let me search.answer",
                    "model": "public-model",
                    "usage": {"input": 7, "output": 2},
                    "finish_reason": "stop",
                }
            }
        )
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_usage_details_and_public_model_identity_cannot_disappear(self):
        stream = GOOD["assembled_stream"]
        self.assertIs(rule.evaluate_one({**GOOD, "assembled_stream": {**stream, "usage": {}}}), False)
        self.assertIs(rule.evaluate_one({**GOOD, "assembled_stream": {**stream, "model": "upstream-name"}}), False)
