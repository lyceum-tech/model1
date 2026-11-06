import json
import unittest

import review_report as report
from review_rules.common import scenarios
from test_gates import GitFixture


class ReportTest(unittest.TestCase):
    def test_enumerated_pull_request_urls(self):
        self.assertEqual(
            report.parse_target("https://github.com/lyceum-tech/lyceum/pull/4292", "unused/repository"),
            ("lyceum-tech/lyceum", 4292),
        )
        self.assertEqual(report.parse_target("42", "owner/repository"), ("owner/repository", 42))
        for target in (
            "https://github.com/lyceum-tech/lyceum/stack/4515",
            "https://example.com/lyceum-tech/lyceum/pull/4292",
            "owner/repository/pull/1",
        ):
            with self.assertRaises(ValueError):
                report.parse_target(target, "owner/repository")

    def test_fixed_rows_expose_unknown_checks_as_not_yet_useful(self):
        markdown = report.render({"base": "a" * 40, "head": "b" * 40, "policy_sha256": "c" * 64, "rules": []})
        rows = [line for line in markdown.splitlines() if line.startswith("|")]
        self.assertEqual(len(rows), 19)
        self.assertTrue(all(len(line.split("|")) == 7 for line in rows))
        self.assertEqual(markdown.count("YELLOW"), 17)
        self.assertEqual(markdown.count("not yet"), 17)

    def test_red_finding_count_survives_reason_truncation(self):
        cells = report._cells({"number": 3, "reason": "x" * 100, "status": "red", "findings": [{"kind": "failure"}]})
        self.assertIn("1 finding(s), use --json for details", cells[-1])
        self.assertLessEqual(len(cells[-1]), 79)

    def test_missing_duplicate_or_errored_scenarios_never_pass(self):
        for facts in (
            None,
            [],
            [{"scenario": "a"}],
            [{"scenario": "a"}, {"scenario": "a"}],
            [{"scenario": "a", "error": "unavailable"}, {"scenario": "b"}],
        ):
            self.assertEqual(scenarios(facts, ("a", "b"), lambda _: True)["status"], "yellow")

    def test_shared_or_unfamiliar_code_is_unknown_rather_than_unaffected(self):
        self.assertIsNone(report.scoped(["new-service/main.go"], ("iris/",)))
        self.assertFalse(report.scoped(["docs/readme.md"], ("iris/",)))


class EvidenceBindingTest(GitFixture):
    def test_candidate_files_and_wrong_head_observations_cannot_make_a_rule_green(self):
        base = self.commit()
        self.write("iris/inference_proxy/client.go", "package proxy\n")
        self.write("docs/observations.json", '{"status":"green"}')
        head = self.commit()

        def color(observations):
            return report.assess(self.repo, base, head, observations)["rules"][3]["status"]

        facts = [
            {
                "scenario": name,
                "actual_status": 200,
                "contract_status": 200,
                "required_fields": ["id"],
                "response_fields": ["id"],
            }
            for name in ("sdk", "public-routing", "response-schema")
        ]
        envelope = {"base": base, "head": head, "policy_sha256": report.policy_digest(), "rules": {"4": facts}}
        self.assertEqual(color(None), "yellow")
        self.assertEqual(color({**envelope, "head": "0" * 40}), "yellow")
        self.assertEqual(color({**envelope, "policy_sha256": "stale"}), "yellow")
        self.assertEqual(color(json.loads(json.dumps(envelope))), "green")


if __name__ == "__main__":
    unittest.main()
