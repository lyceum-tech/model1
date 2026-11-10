import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import dev_runtime

BASE = "a" * 40
HEAD = "b" * 40
POLICY = "c" * 64


def observations(**changes):
    value = {
        "base": BASE,
        "head": HEAD,
        "policy_sha256": POLICY,
        "runtime": {"candidate_revision_verified": True, "backend": "fake-openai-compatible"},
        "rules": {
            "4": [{"scenario": "sdk", "error": "response-contract-inconclusive"}],
            "5": [{"scenario": "absent", "error": "response-contract-inconclusive"}],
            "7": [{"scenario": "parse-error", "error": "response-contract-inconclusive"}],
            "9": [
                {
                    "scenario": "plain",
                    "comparisons": {"text": True, "model": True, "usage": True, "finish_reason": True},
                }
            ],
            "10": [{"scenario": "cancellation", "error": "response-contract-inconclusive"}],
        },
    }
    value.update(changes)
    return value


class DevRuntimeTest(unittest.TestCase):
    def test_only_an_explicit_non_root_dns_target_is_accepted(self):
        self.assertEqual(dev_runtime.validate_host("pierre@horn.example.invalid"), "pierre@horn.example.invalid")
        for host in (
            None,
            "",
            "horn",
            "root@horn",
            "-root@horn",
            "pierre@horn -oProxyCommand=bad",
            "pierre@-evil",
            "pierre@127.0.0.1",
        ):
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    dev_runtime.validate_host(host)

    def query(self, status=0, stdout=None, stderr=""):
        if stdout is None:
            stdout = json.dumps(observations())
        return SimpleNamespace(returncode=status, stdout=stdout, stderr=stderr)

    def test_ssh_is_batch_only_and_uses_ssh_configuration(self):
        with patch.object(subprocess, "run", return_value=self.query()) as execute:
            self.assertEqual(dev_runtime.collect("pierre@horn", BASE, HEAD, POLICY), observations())
        command = execute.call_args.args[0]
        self.assertIn("BatchMode=yes", command)
        self.assertIn("--", command)
        self.assertNotIn("StrictHostKeyChecking", command)
        self.assertIn(str(HEAD), command[-1])
        self.assertIn("$HOME/.local/bin/stack-review-runtime", command[-1])
        self.assertIn("runtime=stack-review-runtime", command[-1])
        self.assertNotIn("--token", command[-1])
        self.assertEqual(execute.call_args.kwargs["timeout"], 2145)

    def test_full_check_results_use_the_extended_deadline_and_strict_schema(self):
        results = observations(
            rules={
                **observations()["rules"],
                "3": {
                    "checks": [
                        {"name": name, "status": "passed"}
                        for name in ("pre-commit", "lint", "test-fast", "integration")
                    ]
                },
            }
        )
        with patch.object(subprocess, "run", return_value=self.query(stdout=json.dumps(results))) as execute:
            self.assertEqual(dev_runtime.collect("pierre@horn", BASE, HEAD, POLICY, tests=True), results)
        command = execute.call_args.args[0][-1]
        self.assertIn("--dev-tests", command)
        self.assertEqual(execute.call_args.kwargs["timeout"], 10845)
        for invalid in (observations(), {**results, "rules": {**results["rules"], "3": {"raw": "secret"}}}):
            with self.subTest(invalid=invalid), patch.object(
                subprocess, "run", return_value=self.query(stdout=json.dumps(invalid))
            ):
                with self.assertRaises(ValueError):
                    dev_runtime.collect("pierre@horn", BASE, HEAD, POLICY, tests=True)

    def test_bad_commit_binding_or_unexpected_backend_is_rejected(self):
        cases = (
            observations(head="c" * 40),
            observations(policy_sha256="0" * 64),
            observations(runtime={"backend": "real"}),
        )
        for data in cases:
            with (
                self.subTest(data=data),
                patch.object(subprocess, "run", return_value=self.query(stdout=json.dumps(data))),
            ):
                with self.assertRaises(ValueError):
                    dev_runtime.collect("pierre@horn", BASE, HEAD, POLICY)

    def test_malformed_and_oversized_remote_output_is_rejected(self):
        for output in (
            "",
            "hello",
            "[]",
            '{"base":' + "a" * 40 + "}",
            json.dumps(observations()) + "x" * (dev_runtime.MAX_OBSERVATION_BYTES + 1),
        ):
            with (
                self.subTest(length=len(output)),
                patch.object(subprocess, "run", return_value=self.query(stdout=output)),
            ):
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    dev_runtime.collect("pierre@horn", BASE, HEAD, POLICY)

    def test_remote_failure_does_not_echo_candidate_output(self):
        with patch.object(subprocess, "run", return_value=self.query(status=1, stderr="Bearer private-token")):
            with self.assertRaises(ValueError) as error:
                dev_runtime.collect("pierre@horn", BASE, HEAD, POLICY)
        self.assertNotIn("private-token", str(error.exception))
        self.assertIn("cleanup", str(error.exception))

    def test_known_compose_failure_is_reported_without_forwarding_arbitrary_stderr(self):
        remote_error = "stack-review-runtime: candidate runtime test failed: docker compose build failed\n"
        with patch.object(subprocess, "run", return_value=self.query(status=1, stderr=remote_error)):
            with self.assertRaises(ValueError) as error:
                dev_runtime.collect("pierre@horn", BASE, HEAD, POLICY)
        self.assertIn("docker compose build failed", str(error.exception))
        self.assertIn("cleanup", str(error.exception))

    def test_invalid_timeout_is_refused(self):
        for timeout in (False, 0, 30, 3601, "60"):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    dev_runtime.collect("pierre@horn", BASE, HEAD, POLICY, timeout=timeout)


if __name__ == "__main__":
    unittest.main()
