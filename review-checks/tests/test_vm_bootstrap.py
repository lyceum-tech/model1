import subprocess
import unittest
from pathlib import Path


BOOTSTRAP = Path(__file__).parents[1] / "vm" / "bootstrap.sh"


class BootstrapTest(unittest.TestCase):
    def run_bootstrap(self, *arguments):
        return subprocess.run(
            ["bash", str(BOOTSTRAP), *arguments],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def test_help_does_not_require_root_or_network(self):
        result = self.run_bootstrap("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("existing Ubuntu or Debian Docker host", result.stdout)
        self.assertIn("private keys must never be copied", result.stdout)

    def test_authentication_selects_the_existing_gh_identity_without_token_arguments(self):
        script = BOOTSTRAP.read_text()
        self.assertIn('gh auth switch --hostname github.com --user "$github_user"', script)
        self.assertIn("gh auth login --hostname github.com --git-protocol https --web", script)
        self.assertIn("gh api user --jq .login", script)
        self.assertNotIn("--with-token", script)
        self.assertNotIn("github_token", script)

    def test_rejects_options_without_values(self):
        for option in ("--branch", "--repository", "--github-user", "--ssh-public-key"):
            with self.subTest(option=option):
                result = self.run_bootstrap(option)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("requires a value", result.stderr)

    def test_rejects_invalid_repository_and_branch_before_installation(self):
        for arguments, message in (
            (("--branch", "bad..branch"), "invalid branch"),
            (("--branch", "-bad"), "invalid branch"),
            (("--repository", "file:///tmp/model1.git"), "HTTPS Git URL"),
            (("--github-user", "invalid_name"), "valid GitHub username"),
            (("--github-user", "-invalid"), "valid GitHub username"),
            ((), "github-user is required"),
            (("unexpected",), "unknown argument"),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_bootstrap(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)


if __name__ == "__main__":
    unittest.main()
