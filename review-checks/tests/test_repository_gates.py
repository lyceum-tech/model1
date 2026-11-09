"""Regression fixtures for reviewer checks against immutable Git snapshots."""

import json
import unittest
from unittest.mock import patch

import repository_checks as checks
from test_gates import GitFixture


class ConfigurationTest(GitFixture):
    def setUp(self):
        super().setUp()
        self.rules: dict = {
            "environments": {name: f"inventory/{name}.yml" for name in ("devel", "staging", "production")},
            "configuration": {"PORT": {"type": "port"}, "SECRET": {"type": "sops"}},
        }
        self.policy_patch = patch("repository_checks.policy", return_value=self.rules)
        self.policy_patch.start()
        self.addCleanup(self.policy_patch.stop)
        for path in self.rules["environments"].values():
            self.write(path, 'PORT: "9462"\nSECRET: ENC[AES256_GCM,data:fixture,type:str]\n')

    def check(self):
        return checks.configuration_check(checks.Snapshot(self.repo, self.commit()))

    def test_all_environments_are_checked_without_decryption(self):
        self.assertEqual(self.check()["status"], "passed")
        self.write("inventory/staging.yml", 'PORT: "0"\nSECRET: ""\n')
        result = self.check()
        self.assertEqual({f["key"] for f in result["findings"]}, {"PORT", "SECRET"})
        self.assertEqual({f["path"] for f in result["findings"]}, {"inventory/staging.yml"})

    def test_missing_file_duplicates_and_wrong_types_fail(self):
        for text in ("PORT: 42\nPORT: 43\n", "PORT: true\n", "PORT: null\n", "PORT: 65536\n"):
            self.write("inventory/devel.yml", text)
            self.assertEqual(self.check()["status"], "failed")
        (self.repo / "inventory/devel.yml").unlink()
        self.assertEqual(self.check()["status"], "failed")

    def test_values_and_yaml_errors_are_not_disclosed(self):
        for text in ('PORT: "canary-secret"\nSECRET: canary-secret\n', "PORT: [canary-secret\n"):
            self.write("inventory/production.yml", text)
            self.assertNotIn("canary-secret", json.dumps(self.check()))

    def test_environment_exceptions_are_explicit_in_trusted_policy(self):
        self.rules["configuration"]["SECRET"]["environments"] = ["production"]
        self.write("inventory/staging.yml", "PORT: 9462\n")
        self.assertEqual(self.check()["status"], "passed")

    def test_candidate_cannot_weaken_the_policy_or_override_snapshot(self):
        self.write("gate_policy.json", "{}")
        revision = self.commit()
        self.write("inventory/staging.yml", "PORT: 0\n")
        self.assertEqual(checks.configuration_check(checks.Snapshot(self.repo, revision))["status"], "passed")
        self.assertEqual(self.check()["status"], "failed")


class ReferenceTest(GitFixture):
    def test_deleting_script_breaks_unchanged_hook_and_mise_task(self):
        self.write("scripts/check.py", "pass\n")
        self.write(".pre-commit-config.yaml", "repos:\n  - hooks:\n      - entry: ./scripts/check.py\n")
        self.write("mise.toml", '[tasks.check]\nrun = "$LYC_PATH_REPO_ROOT/scripts/check.py"\n')
        base = checks.Snapshot(self.repo, self.commit())
        (self.repo / "scripts/check.py").unlink()
        result = checks.reference_check(base, checks.Snapshot(self.repo, self.commit()))
        self.assertEqual(result["status"], "failed")
        self.assertEqual({f["path"] for f in result["findings"]}, {".pre-commit-config.yaml", "mise.toml"})

    def test_new_reference_fails_existing_debt_does_not(self):
        self.write("mise.toml", '[tasks.old]\nrun = "scripts/old"\n')
        base = checks.Snapshot(self.repo, self.commit())
        self.write("README.md", "Unrelated edit\n")
        self.assertEqual(checks.reference_check(base, checks.Snapshot(self.repo, self.commit()))["status"], "passed")
        self.write("mise.toml", '[tasks.new]\nrun = "scripts/new"\n')
        self.assertEqual(checks.reference_check(base, checks.Snapshot(self.repo, self.commit()))["status"], "failed")

    def test_action_needs_metadata_and_renames_must_update_callers(self):
        base = checks.Snapshot(self.repo, self.commit())
        self.write(".github/workflows/check.yml", "jobs:\n  test:\n    steps:\n      - uses: ./.github/actions/check\n")
        self.write(".github/actions/check/README.md", "Not an action\n")
        self.assertEqual(checks.reference_check(base, checks.Snapshot(self.repo, self.commit()))["status"], "failed")
        self.write(".github/actions/check/action.yml", "name: Check\n")
        self.assertEqual(checks.reference_check(base, checks.Snapshot(self.repo, self.commit()))["status"], "passed")

    def test_invalid_config_is_incomplete_without_disclosing_parser_input(self):
        base = checks.Snapshot(self.repo, self.commit())
        self.write("mise.toml", "canary-secret = [")
        result = checks.reference_check(base, checks.Snapshot(self.repo, self.commit()))
        self.assertEqual(result["status"], "incomplete")
        self.assertNotIn("canary-secret", json.dumps(result))

    def test_known_generator_output_and_destination_are_checked_without_execution(self):
        base = checks.Snapshot(self.repo, self.commit())
        contract = {
            "source": "aliases.json",
            "target": "copy.json",
            "generator": "scripts/generate",
        }
        self.write("aliases.json", '{"vendor_aliases": {"old": "new"}}')
        self.write(
            "scripts/generate",
            'SOURCE = REPO_ROOT / "aliases.json"\nCONTROLLER = REPO_ROOT / "copy.json"\n'
            'raise RuntimeError("must not execute")\n',
        )
        self.write(
            "copy.json",
            json.dumps(
                {
                    "_generated": "generated from aliases.json. Do not modify: edit the JSON and run scripts/generate.",
                    "aliases": {"old": "new"},
                }
            ),
        )
        with patch("repository_checks.policy", return_value={"generators": [contract]}):
            self.assertEqual(
                checks.reference_check(base, checks.Snapshot(self.repo, self.commit()))["status"], "passed"
            )
            self.write("aliases.json", '{"vendor_aliases": {"old": "different"}}')
            result = checks.reference_check(base, checks.Snapshot(self.repo, self.commit()))
            self.assertEqual(result["findings"][0]["kind"], "stale-generated-output")
            self.write(
                "scripts/generate", 'SOURCE = REPO_ROOT / "aliases.json"\nCONTROLLER = REPO_ROOT / "retired.json"\n'
            )
            result = checks.reference_check(base, checks.Snapshot(self.repo, self.commit()))
            self.assertIn("generator-destination-changed", {f["kind"] for f in result["findings"]})
            (self.repo / "copy.json").unlink()
            result = checks.reference_check(base, checks.Snapshot(self.repo, self.commit()))
            self.assertEqual(result["findings"][0]["kind"], "missing-generator-input-or-output")


class CoverageTest(GitFixture):
    def setUp(self):
        super().setUp()
        self.rules = {
            "validation": {
                "tasks": {"infra/terraform/mise.toml": {"lint": {"run": "scripts/lint", "depends": [":validate"]}}},
                "workflow_tasks": {".github/workflows/check.yml": ["//...:lint", "//...:test-fast"]},
                "implementations": [],
                "environments": ["devel", "staging", "production"],
            }
        }
        self.policy_patch = patch("repository_checks.policy", return_value=self.rules)
        self.policy_patch.start()
        self.addCleanup(self.policy_patch.stop)
        self.write("infra/terraform/mise.toml", '[tasks.lint]\nrun = "scripts/lint"\ndepends = [":validate"]\n')
        self.workflow = (
            "jobs:\n  test:\n    steps:\n      - run: mise run '//...:lint'\n      - run: mise run '//...:test-fast'\n"
        )
        self.write(".github/workflows/check.yml", self.workflow)
        for name in ("devel", "staging", "production"):
            self.write(f"infra/terraform/envs/{name}.env", "# fixture\n")

    def check(self):
        return checks.validation_coverage_check(checks.Snapshot(self.repo, self.commit()))

    def test_removing_validate_dependency_fails_even_if_task_name_survives(self):
        self.assertEqual(self.check()["status"], "passed")
        self.write("infra/terraform/mise.toml", '[tasks.lint]\nrun = "scripts/lint"\n')
        self.assertEqual(self.check()["findings"][0]["kind"], "validator-task-removed")

    def test_missing_ci_call_or_environment_fails(self):
        self.write(".github/workflows/check.yml", self.workflow.replace("mise run '//...:lint'", "echo '//...:lint'"))
        (self.repo / "infra/terraform/envs/staging.env").unlink()
        self.assertEqual({f["kind"] for f in self.check()["findings"]}, {"ci-task-removed", "environment-removed"})

    def test_script_rewrite_cannot_pass_by_retaining_its_task_name(self):
        self.rules["validation"]["implementations"] = ["mise/scripts/terraform-lint.bash"]
        self.write("mise/scripts/terraform-lint.bash", "#!/bin/bash\nexit 0\n")
        result = self.check()
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["findings"][0]["kind"], "validator-implementation-changed")

    def test_echoed_or_disabled_ci_commands_do_not_supply_coverage(self):
        for replacement in ("echo mise run '//...:lint'", "mise run '//...:lint'\n        if: false"):
            self.write(".github/workflows/check.yml", self.workflow.replace("mise run '//...:lint'", replacement))
            self.assertEqual(self.check()["status"], "failed")

    def test_container_results_cover_all_groups_and_report_failures(self):
        results = {
            "checks": [
                {"name": name, "status": "passed"} for name in ("pre-commit", "lint", "test-fast", "integration")
            ]
        }
        passed = checks.validation_coverage_check(checks.Snapshot(self.repo, self.commit()), results)
        self.assertEqual(passed["status"], "passed")
        self.assertIn("All Lyceum container check groups passed", passed["reason"])
        results["checks"][1]["status"] = "failed"
        failed = checks.validation_coverage_check(checks.Snapshot(self.repo, "HEAD"), results)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["findings"], [{"rule": "CI-3", "kind": "runtime-check-failed", "check": "lint"}])

    def test_malformed_or_incomplete_container_results_cannot_pass(self):
        revision = self.commit()
        for results in (None, {"checks": []}, {"checks": [{"name": "lint", "status": "ok"}]}):
            with self.subTest(results=results):
                observations = {"unexpected": True} if results is None else results
                result = checks.validation_coverage_check(checks.Snapshot(self.repo, revision), observations)
                self.assertEqual(result["status"], "incomplete")


if __name__ == "__main__":
    unittest.main()
