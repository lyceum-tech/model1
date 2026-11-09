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
        self.assertIn("private keys must never be copied", result.stdout.lower())

    def test_authentication_selects_the_existing_gh_identity_without_token_arguments(self):
        script = BOOTSTRAP.read_text()
        self.assertIn('gh auth switch --hostname github.com --user "$github_user"', script)
        self.assertIn('runuser -u "$runtime_user" -- env HOME="$runtime_home"', script)
        self.assertIn("as_runtime_user env BROWSER=echo gh auth login", script)
        self.assertIn("gh api user --jq .login", script)
        self.assertIn('runtime_dir="$runtime_home/.stack-review"', script)
        self.assertNotIn('"$runtime_home/venv"', script)
        self.assertNotIn("--with-token", script)
        self.assertNotIn("github_token", script)

    def test_buildx_is_checksum_verified_for_the_runtime_user(self):
        script = BOOTSTRAP.read_text()
        self.assertIn("readonly BUILDX_VERSION=0.30.1", script)
        self.assertIn("docker buildx version", script)
        self.assertIn("dpkg --compare-versions", script)
        self.assertIn('sub(/^\\*/, "", name)', script)
        self.assertIn("as_runtime_user curl", script)
        self.assertIn("as_runtime_user sha256sum", script)
        self.assertIn("as_runtime_user docker buildx version", script)
        self.assertIn("/usr/local/lib/docker/cli-plugins/docker-buildx", script)

    def test_public_keys_are_appended_without_replacing_existing_ones(self):
        script = BOOTSTRAP.read_text()
        self.assertIn('grep -Fqx -f "$ssh_public_key" "$authorized_keys"', script)
        self.assertIn('cat "$ssh_public_key" >> "$authorized_keys"', script)
        self.assertNotIn('"$ssh_public_key" "$authorized_keys"\n', script)

    def test_rejects_options_without_values(self):
        options = ("--branch", "--repository", "--github-user", "--runtime-user", "--ssh-public-key")
        for option in options:
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
            (
                ("--runtime-user", "../root", "--github-user", "pierrot-la-lune"),
                "invalid Linux runtime username",
            ),
            (
                ("--runtime-user", "-root", "--github-user", "pierrot-la-lune"),
                "invalid Linux runtime username",
            ),
            ((), "github-user is required"),
            (("unexpected",), "unknown argument"),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_bootstrap(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)


if __name__ == "__main__":
    unittest.main()
