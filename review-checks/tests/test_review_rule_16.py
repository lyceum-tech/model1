"""Independent regressions for rule 16: Scoped CI publishing credentials."""

import json
import unittest

from review_rules import rule_16 as rule

GOOD: dict = {
    "ci_principals": ["build-agent"],
    "allowed_repositories": ["production/image-a"],
    "grants": [
        {
            "principal": "build-agent",
            "role": "roles/artifactregistry.writer",
            "scope": "repository",
            "resource": "production/image-a",
            "production": True,
            "allowed_branches": ["refs/heads/main"],
        }
    ],
}


class RuleTest(unittest.TestCase):
    def test_complete_observations_pass_and_counterexample_fails(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        self.assertEqual(rule.evaluate(facts)["status"], "green")
        facts[0].update(
            {
                "grants": [
                    {
                        "principal": "build-agent",
                        "role": "roles/artifactregistry.writer",
                        "scope": "project",
                        "resource": "production",
                        "production": True,
                        "allowed_branches": ["*"],
                    }
                ]
            }
        )
        self.assertEqual(rule.evaluate(facts)["status"], "red")

    def test_absent_partial_and_malformed_observations_are_unknown(self):
        facts = [{"scenario": name, **json.loads(json.dumps(GOOD))} for name in rule.REQUIRED]
        for value in (None, [], facts[:-1], [{"scenario": rule.REQUIRED[0]}]):
            self.assertEqual(rule.evaluate(value)["status"], "yellow")

    def test_repository_scope_alone_does_not_allow_arbitrary_production_branch_publishing(self):
        grant = {**GOOD["grants"][0], "allowed_branches": ["*"]}
        self.assertIs(rule.evaluate_one({**GOOD, "grants": [grant]}), False)
