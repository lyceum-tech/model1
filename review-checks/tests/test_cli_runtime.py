import io
import json
import sys
import unittest
from unittest.mock import patch

import review_report
from git_fixture import GitFixture
from test_dev_runtime import observations


class CommandTest(GitFixture):
    def setUp(self):
        super().setUp()
        self.write("app/src/example.py", "# base\n")
        self.base = self.commit()
        self.write("app/src/example.py", "# candidate\n")
        self.head = self.commit()

    def evaluate(self, json_mode=False, tests=False):
        pr = {
            "state": "open",
            "title": "Runtime fixture",
            "html_url": "https://github.com/lyceum-tech/lyceum/pull/4292",
            "base": {"ref": "main", "sha": self.base},
            "head": {"sha": self.head},
        }
        observations_by_candidate = observations(
            base=self.base, head=self.head, policy_sha256=review_report.policy_digest()
        )
        arguments = [
            "stack-review",
            "--dev-vm",
            "pierre@horn",
            "--cache-dir",
            str(self.repo / "local-only-cache"),
            "https://github.com/lyceum-tech/lyceum/pull/4292",
        ]
        if json_mode:
            arguments.insert(-1, "--json")
        if tests:
            arguments.insert(-1, "--dev-tests")
        output = io.StringIO()
        with (
            patch.object(sys, "argv", arguments),
            patch.object(sys, "stdout", output),
            patch.object(review_report, "gh", return_value=pr),
            patch.object(review_report, "prepare_cache", return_value=self.repo) as cache,
            patch("dev_runtime.collect", return_value=observations_by_candidate) as collect,
        ):
            self.assertEqual(review_report.main(), 0)
        collect.assert_called_once_with(
            "pierre@horn", self.base, self.head, review_report.policy_digest(), tests=tests
        )
        self.assertEqual(cache.call_args.args[0], "lyceum-tech/lyceum")
        return output.getvalue()

    def test_exact_command_renders_all_rows_with_explicit_partial_evidence(self):
        output = self.evaluate()
        self.assertEqual(len([line for line in output.splitlines() if line.startswith("|")]), 27)
        self.assertIn("25 checks:", output)
        self.assertIn("plain passed", output)
        self.assertIn(self.head, output)

    def test_json_has_bound_partial_scenario_evidence(self):
        result = json.loads(self.evaluate(json_mode=True))
        self.assertEqual(result["head"], self.head)
        self.assertEqual(result["policy_sha256"], review_report.policy_digest())
        self.assertEqual(len(result["rules"]), 25)
        self.assertEqual(result["rules"][8]["status"], "yellow")
        self.assertIn("missing scenarios", result["rules"][8]["reason"])

    def test_full_development_checks_are_opt_in(self):
        self.evaluate(tests=True)


if __name__ == "__main__":
    unittest.main()
