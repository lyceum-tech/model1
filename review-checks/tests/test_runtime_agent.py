import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import runtime_agent
from git_fixture import GitFixture


FAKE_DOCKER = r"""#!/usr/bin/env python3
import json
import os
import pathlib
import sys

args = sys.argv[1:]
with open(os.environ["REVIEW_TEST_LOG"], "a") as log:
    log.write(json.dumps(args) + "\n")
if args[:1] == ["compose"]:
    action = args[5]
    if action == "exec":
        if os.environ.get("REVIEW_TEST_FAIL") == "exec":
            sys.exit(1)
        canary = os.environ["REVIEW_CANARY"]
        print(json.dumps({
            "4": [
                {"scenario": scenario, "actual_status": 200, "contract_status": 200,
                 "required_fields": ["id"], "response_fields": ["id"]}
                for scenario in ("sdk", "public-routing", "response-schema")
            ],
            "5": [
                {"scenario": scenario, "forwarded": False, "accepted": False, "status": 400,
                 "normalized": None, "validated": None, "upstream_value": None, "ambiguous_aliases": False}
                for scenario in ("absent", "null", "empty", "wrong-type", "zero", "negative", "conflicting-aliases")
            ],
            "7": [
                {"scenario": scenario, "canaries": [canary + "-" + scenario], "client_error": "http-500"}
                for scenario in ("parse-error", "timeout", "redirect", "upstream-error")
            ],
            "9": [
                {"scenario": scenario, "comparisons": {"text": True, "model": True, "usage": True, "finish_reason": True}}
                for scenario in ("plain", "tools", "search", "stop-string")
            ],
            "10": [
                {"scenario": scenario, "idle_limit_ms": 3000,
                 "events": [{"turn": 1, "kind": "content", "time_ms": 1}, {"turn": 1, "kind": "done", "time_ms": 2}]}
                for scenario in ("string-argument", "array-argument", "object-argument", "cancellation", "invalid-message", "queue-pressure")
            ],
        }))
    elif action == "logs":
        print("candidate log output without review canaries")
    elif action == "images":
        print("a" * 64)
    elif action == os.environ.get("REVIEW_TEST_FAIL", "") or (
        action == "up" and os.environ.get("REVIEW_TEST_FAIL") == "up"
    ):
        sys.exit(1)
    elif action == "down":
        with open(os.environ["REVIEW_TEST_CLEANUP"], "a") as result:
            result.write(args[2] + "\n")
    elif action == "build":
        source = pathlib.Path(os.environ["CANDIDATE_SOURCE"])
        with open(os.environ["REVIEW_TEST_BUILD"], "w") as result:
            result.write((source / "iris/inference_proxy/Dockerfile").read_text())
elif args[:1] == ["image"] and args[1:2] == ["inspect"]:
    print(os.environ.get("REVIEW_TEST_IMAGE_LABEL", os.environ["CANDIDATE_HEAD"]))
"""


class LifecycleTest(GitFixture):
    def setUp(self):
        super().setUp()
        self.write("iris/inference_proxy/Dockerfile", "FROM fixture\nARG BUILD_COMMIT\n")
        self.base = self.commit()
        self.write("iris/inference_proxy/Dockerfile", "FROM candidate\nARG BUILD_COMMIT\n")
        self.head = self.commit()
        self.home = Path(self.directory.name) / "runtime-home"
        self.bin_dir = Path(self.directory.name) / "bin"
        self.bin_dir.mkdir()
        self.docker = self.bin_dir / "docker"
        self.docker.write_text(FAKE_DOCKER)
        self.docker.chmod(0o755)
        self.log = Path(self.directory.name) / "docker.log"
        self.cleanup = Path(self.directory.name) / "cleanup.log"
        self.build = Path(self.directory.name) / "build.log"
        self.env = patch.dict(
            os.environ,
            {
                "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
                "REVIEW_TEST_LOG": str(self.log),
                "REVIEW_TEST_CLEANUP": str(self.cleanup),
                "REVIEW_TEST_BUILD": str(self.build),
            },
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.prepare = patch.object(runtime_agent, "prepare_repository", return_value=self.repo)
        self.prepare.start()
        self.addCleanup(self.prepare.stop)

    def collect(self):
        return runtime_agent.collect(self.base, self.head, home=self.home)

    def test_exact_head_is_archived_and_resources_are_cleaned(self):
        data = self.collect()
        self.assertEqual(data["runtime"]["candidate_revision_verified"], True)
        self.assertEqual(data["head"], self.head)
        self.assertEqual(self.build.read_text(), "FROM candidate\nARG BUILD_COMMIT\n")
        self.assertEqual(data["rules"]["9"][0]["comparisons"]["text"], True)
        self.assertEqual(set(data["rules"]), {"4", "5", "7", "9", "10"})
        self.assertEqual(data["rules"]["7"][0]["captured_logs"], "")
        self.assertNotIn("review-canary-", json.dumps(data["rules"]["4"] + data["rules"]["5"] + data["rules"]["10"]))
        self.assertIn("stack-review-", self.cleanup.read_text())
        self.assertFalse(any((self.home / "runs").iterdir()))
        commands = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(commands[-1][5], "down")
        self.assertEqual(commands[-1][6:8], ["--volumes", "--remove-orphans"])
        self.assertNotIn("CANDIDATE_HEAD", self.build.read_text())
        inspections = [command for command in commands if command[:2] == ["image", "inspect"]]
        self.assertEqual(len(inspections), 1)
        self.assertTrue(inspections[0][2].startswith(f"stack-review-{self.head[:12]}-"))
        self.assertTrue(inspections[0][2].endswith(":candidate"))
        self.assertNotIn("images", [command[5] for command in commands if command[:1] == ["compose"]])

    def test_mismatched_image_revision_never_becomes_evidence(self):
        with patch.dict(os.environ, {"REVIEW_TEST_IMAGE_LABEL": self.base}):
            with self.assertRaises(RuntimeError):
                self.collect()
        self.assertIn("down", self.log.read_text())
        self.assertNotIn('"exec"', self.log.read_text())

    def test_failed_build_startup_and_probe_always_clean_up(self):
        for failure in ("build", "up", "exec"):
            with self.subTest(failure=failure), patch.dict(os.environ, {"REVIEW_TEST_FAIL": failure}):
                with self.assertRaises(RuntimeError):
                    self.collect()
                self.assertIn("down", self.log.read_text())

    def test_failed_cleanup_is_not_reported_as_success(self):
        with patch.dict(os.environ, {"REVIEW_TEST_FAIL": "down"}):
            with self.assertRaises(RuntimeError):
                self.collect()
        commands = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(commands[-2][5], "rm")
        self.assertEqual(commands[-1][5], "down")

    def test_timeout_during_build_still_cleans_up(self):
        import subprocess

        commands = []

        def execute(_compose, *arguments, **_options):
            commands.append(arguments)
            if arguments[0] == "build":
                raise subprocess.TimeoutExpired(arguments, 1500)

        with patch.object(runtime_agent.Compose, "execute", execute):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.collect()
        self.assertTrue(any(arguments[0] == "down" and "--volumes" in arguments for arguments in commands))

    def test_another_run_is_not_interrupted(self):
        import fcntl

        (self.home / "runs").mkdir(parents=True)
        with (self.home / "runtime.lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(RuntimeError):
                self.collect()

    def test_invalid_commits_cannot_create_resources(self):
        for value in ("HEAD", "a" * 39, "-c", "a" * 40 + ";rm"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    runtime_agent.collect(value, self.head, home=self.home)
        self.assertFalse(self.log.exists())


class EvidenceTest(unittest.TestCase):
    def valid(self):
        return {
            "4": [
                {"scenario": scenario, "actual_status": 200, "contract_status": 200,
                 "required_fields": ["id"], "response_fields": ["id"]}
                for scenario in runtime_agent.PROBE_SCENARIOS["4"]
            ],
            "5": [
                {"scenario": scenario, "forwarded": False, "accepted": False, "status": 400,
                 "normalized": None, "validated": None, "upstream_value": None, "ambiguous_aliases": False}
                for scenario in runtime_agent.PROBE_SCENARIOS["5"]
            ],
            "7": [
                {"scenario": scenario, "canaries": [f"review-canary-test-{scenario}"], "client_error": "http-500"}
                for scenario in runtime_agent.PROBE_SCENARIOS["7"]
            ],
            "9": [
                {"scenario": scenario, "comparisons": {"text": True, "model": True, "usage": True, "finish_reason": True}}
                for scenario in runtime_agent.PROBE_SCENARIOS["9"]
            ],
            "10": [
                {"scenario": scenario, "idle_limit_ms": 3000,
                 "events": [{"turn": 1, "kind": "content", "time_ms": 1}, {"turn": 1, "kind": "done", "time_ms": 2}]}
                for scenario in runtime_agent.PROBE_SCENARIOS["10"]
            ],
        }

    def test_malformed_probe_output_is_rejected(self):
        duplicate = json.loads(json.dumps(self.valid()))
        duplicate["9"][1]["scenario"] = "plain"
        non_boolean = json.loads(json.dumps(self.valid()))
        non_boolean["9"][1]["comparisons"]["text"] = "yes"
        unexpected_field = json.loads(json.dumps(self.valid()))
        unexpected_field["4"][0]["raw"] = "secret response"
        bad_event = json.loads(json.dumps(self.valid()))
        bad_event["10"][0]["events"][0]["kind"] = "mystery"
        bool_status = json.loads(json.dumps(self.valid()))
        bool_status["5"][0]["status"] = True
        missing_rule = json.loads(json.dumps(self.valid()))
        del missing_rule["10"]
        cases = [[], {}, duplicate, non_boolean, unexpected_field, bad_event, bool_status, missing_rule]
        for output in [*(json.dumps(case) for case in cases), "x" * (runtime_agent.MAX_PROBE_BYTES + 1)]:
            with self.subTest(output=output[:80]), patch.object(runtime_agent, "checked", return_value=output):
                with self.assertRaises((ValueError, RuntimeError, KeyError, TypeError, json.JSONDecodeError)):
                    runtime_agent.probe_facts("stack-review", os.environ.copy())

    def test_anonymous_http_error_remains_inconclusive(self):
        expected = self.valid()
        expected["9"][1] = {"scenario": "tools", "error": "response-contract-inconclusive"}
        with patch.object(runtime_agent, "checked", return_value=json.dumps(expected)) as execute:
            facts = runtime_agent.probe_facts("stack-review", os.environ.copy())
        self.assertEqual(facts, expected)
        self.assertEqual(execute.call_args.args[0][-1], "--all")
        self.assertNotIn("Bearer", json.dumps(facts))

    def test_log_enrichment_searches_bound_canaries_without_forwarding_logs(self):
        facts = self.valid()["7"]
        prefix = "review-canary-test"
        leaked = runtime_agent.enrich_log_facts(facts, f"prefix {prefix}-timeout suffix", prefix)
        self.assertEqual(leaked[1]["captured_logs"], f"{prefix}-timeout")
        self.assertEqual(leaked[0]["captured_logs"], "")
        missing = runtime_agent.enrich_log_facts(facts, None, prefix)
        self.assertTrue(all(fact.get("error") == "response-contract-inconclusive" for fact in missing))
        with self.assertRaises(RuntimeError):
            runtime_agent.enrich_log_facts(facts, "logs", "review-canary-other")


class DevelopmentCheckTest(GitFixture):
    def test_real_git_snapshot_is_reset_after_precommit_and_checks_all_groups(self):
        source = Path(self.directory.name) / "candidate"
        source.mkdir()
        (source / "mise.toml").write_text("")
        (source / "go.mod").write_text("original\n")
        runner = Path(self.directory.name) / "dev"
        log = Path(self.directory.name) / "dev-checks.json"
        runner.write_text(
            """#!/usr/bin/env python3
import json
import os
import pathlib
import sys
source = pathlib.Path(os.environ["LYCEUM_DEV_REPO"])
with open(os.environ["REVIEW_DEV_LOG"], "a") as stream:
    stream.write(json.dumps({"command": sys.argv[1], "repo": str(source), "has_gpg": "LYCEUM_DEV_GNUPG" in os.environ}) + "\\n")
if sys.argv[1] == "pre-commit":
    (source / "go.mod").write_text("modified\\n")
    (source / "untracked").write_text("discard me\\n")
    sys.exit(1)
if sys.argv[1] not in ("build", "pre-commit"):
    if (source / "go.mod").read_text() != "original\\n" or (source / "untracked").exists():
        sys.exit(2)
"""
        )
        runner.chmod(0o755)
        with (
            patch.object(runtime_agent, "DEV_RUNNER", runner),
            patch.dict(os.environ, {"REVIEW_DEV_LOG": str(log), "LYCEUM_DEV_GNUPG": "/must-not-be-shared"}),
        ):
            facts = runtime_agent.development_check_facts(source, os.environ.copy())
        self.assertEqual(
            facts,
            {
                "checks": [
                    {"name": "pre-commit", "status": "failed"},
                    {"name": "lint", "status": "passed"},
                    {"name": "test-fast", "status": "passed"},
                    {"name": "integration", "status": "passed"},
                ]
            },
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual([call["command"] for call in calls], ["build", "pre-commit", "lint", "test", "integration"])
        self.assertTrue(all(call["repo"] == str(source) and not call["has_gpg"] for call in calls))
        self.assertEqual((source / "go.mod").read_text(), "original\n")
        self.assertFalse((source / "untracked").exists())


class ArchiveTest(GitFixture):
    def test_commit_archive_does_not_use_the_worktree(self):
        self.write("path/file", "committed")
        commit = self.commit()
        self.write("path/file", "uncommitted")
        target = Path(self.directory.name) / "archive"
        runtime_agent.archive_commit(self.repo, commit, target, os.environ.copy())
        self.assertEqual((target / "path/file").read_text(), "committed")


if __name__ == "__main__":
    unittest.main()
