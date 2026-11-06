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
        print(json.dumps({"scenario": "plain", "comparisons": {"text": True, "model": True, "usage": True, "finish_reason": True}}))
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
    def test_malformed_probe_output_is_rejected(self):
        for output in (
            "[]",
            '{"scenario":"plain","raw":"secret response"}',
            '{"scenario":"plain","comparisons":{"text":"yes"}}',
            "x" * (runtime_agent.MAX_PROBE_BYTES + 1),
        ):
            with self.subTest(output=output[:40]), patch.object(runtime_agent, "checked", return_value=output):
                with self.assertRaises((ValueError, RuntimeError, KeyError, json.JSONDecodeError)):
                    runtime_agent.comparison_fact("stack-review", os.environ.copy())

    def test_anonymous_http_error_remains_inconclusive(self):
        with patch.object(
            runtime_agent, "checked", return_value='{"scenario":"plain","error":"response-contract-inconclusive"}'
        ):
            fact = runtime_agent.comparison_fact("stack-review", os.environ.copy())
        self.assertNotIn("response", fact.get("text", ""))
        self.assertNotIn("Bearer", json.dumps(fact))


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
