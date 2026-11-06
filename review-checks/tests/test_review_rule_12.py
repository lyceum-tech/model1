"""Independent regressions for rule 12: Customer URL network boundary."""

import json
import unittest

from review_rules import rule_12 as rule

GOOD = {"hops": [{"dial_ip": "127.0.0.1", "connected": False}]}


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update({"hops": [{"dial_ip": "169.254.169.254", "connected": True}]})
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_redirect_and_mapped_ipv6_cannot_bypass_dial_address_checks(self):
        for ip in ("::ffff:127.0.0.1", "fd00::1", "10.0.0.1"):
            hops = [{"dial_ip": "8.8.8.8", "connected": True}, {"dial_ip": ip, "connected": True}]
            self.assertIs(rule.evaluate_one({"hops": hops}), False)
