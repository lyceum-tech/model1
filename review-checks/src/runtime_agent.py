"""Build and probe one exact Lyceum commit in disposable Docker Compose resources."""

import argparse
import fcntl
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import tarfile
import tempfile
from pathlib import Path

from review_report import policy_digest

REPOSITORY = "lyceum-tech/lyceum"
REPOSITORY_URL = f"https://github.com/{REPOSITORY}.git"
ASSETS = Path(__file__).parent / "runtime_assets"
MAX_PROBE_BYTES = 16 * 1024
COMMIT = re.compile(r"[0-9a-f]{40}")
DEV_RUNNER = ASSETS / "lyceum_dev" / "dev"
DEV_CHECKS = (("pre-commit", "pre-commit"), ("lint", "lint"), ("test-fast", "test"), ("integration", "integration"))


def run_command(command, *, env, timeout, capture=False):
    return subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=capture,
        timeout=timeout,
        check=False,
        env=env,
    )


def checked(command, *, env, timeout, capture=False, stage="runtime command"):
    result = run_command(command, env=env, timeout=timeout, capture=capture)
    if result.returncode != 0:
        raise RuntimeError(f"{stage} failed")
    return result.stdout if capture else None


def valid_commit(value):
    if not COMMIT.fullmatch(value):
        raise ValueError("Expected a full lowercase Git commit")
    return value


class Compose:
    def __init__(self, project, env):
        self.project = project
        self.env = env
        self.prefix = ["docker", "compose", "--project-name", project, "--file", str(ASSETS / "compose.yaml")]

    def execute(self, *arguments, timeout=180, capture=False):
        return checked(
            self.prefix + list(arguments),
            env=self.env,
            timeout=timeout,
            capture=capture,
            stage=f"docker compose {arguments[0]}",
        )

    def cleanup(self):
        try:
            self.execute("down", "--volumes", "--remove-orphans", "--timeout", "20", timeout=90)
        except (RuntimeError, subprocess.SubprocessError, OSError):
            self.execute("rm", "--force", "--stop", "--volumes", timeout=60)
            self.execute("down", "--volumes", "--remove-orphans", "--timeout", "20", timeout=90)


def prepare_repository(root, base, head, env):
    repository = root / "cache" / f"{REPOSITORY.replace('/', '--')}.git"
    origin = subprocess.run(
        ["git", "-C", str(repository), "remote", "get-url", "origin"] if repository.exists() else ["git", "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
    )
    if origin.returncode != 0:
        raise RuntimeError("Candidate cache is invalid")
    if not repository.exists():
        repository.parent.mkdir(parents=True, exist_ok=True)
        checked(["git", "init", "--bare", "--quiet", str(repository)], env=env, timeout=30)
        checked(["git", "-C", str(repository), "remote", "add", "origin", REPOSITORY_URL], env=env, timeout=30)
    elif origin.stdout.strip() != REPOSITORY_URL:
        raise RuntimeError("Candidate cache has an unexpected origin")
    if shutil.which("gh") is None:
        raise RuntimeError("GitHub CLI is not installed")
    checked(["gh", "auth", "status", "--hostname", "github.com"], env=env, timeout=30)
    checked(
        ["git", "-C", str(repository), "fetch", "--filter=blob:none", "origin", base, head],
        env=env,
        timeout=600,
    )
    for commit in (base, head):
        actual = checked(
            ["git", "-C", str(repository), "rev-parse", f"{commit}^{{commit}}"],
            env=env,
            timeout=30,
            capture=True,
        ).strip()
        if actual != commit:
            raise RuntimeError("Candidate revision does not match the pull request")
    ancestor = subprocess.run(
        ["git", "-C", str(repository), "merge-base", "--is-ancestor", base, head],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=30,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("Pull request base is not an ancestor of its head")
    return repository


def archive_commit(repository, commit, destination, env):
    process = subprocess.Popen(
        ["git", "-C", str(repository), "archive", "--format=tar", commit],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    try:
        with process.stdout:
            with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
                archive.extractall(destination, filter="data")
        if process.wait(timeout=60) != 0:
            raise RuntimeError("Candidate archive failed")
    except BaseException:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=30)
        raise


def verify_image(compose, head):
    label = checked(
        [
            "docker",
            "image",
            "inspect",
            compose.env["RUNTIME_IMAGE"],
            "--format",
            '{{index .Config.Labels "org.opencontainers.image.revision"}}',
        ],
        env=compose.env,
        timeout=30,
        capture=True,
    ).strip()
    if label != head:
        raise RuntimeError("Candidate image is not bound to the pull request head")


def comparison_fact(project, env, timeout=600):
    output = checked(
        [
            "docker",
            "compose",
            "--project-name",
            project,
            "--file",
            str(ASSETS / "compose.yaml"),
            "exec",
            "-T",
            "fixture",
            "python",
            "-m",
            "runtime_assets.probe",
            "--all",
        ],
        env=env,
        timeout=timeout,
        capture=True,
    )
    if len(output.encode()) > MAX_PROBE_BYTES:
        raise RuntimeError("Candidate probe exceeded its output budget")
    facts = json.loads(output)
    scenarios = ("plain", "tools", "search", "stop-string")
    if not isinstance(facts, list) or len(facts) != len(scenarios):
        raise RuntimeError("Candidate probe returned missing or duplicate scenarios")
    if [fact.get("scenario") for fact in facts if isinstance(fact, dict)] != list(scenarios):
        raise RuntimeError("Candidate probe returned unexpected scenarios")
    for fact in facts:
        if set(fact) == {"scenario", "comparisons"}:
            if not isinstance(fact["comparisons"], dict) or set(fact["comparisons"]) != {
                "text", "model", "usage", "finish_reason"
            }:
                raise RuntimeError("Candidate probe returned unexpected fields")
            if not all(type(value) is bool for value in fact["comparisons"].values()):
                raise RuntimeError("Candidate probe returned invalid comparisons")
        elif fact != {"scenario": fact["scenario"], "error": "response-contract-inconclusive"}:
            raise RuntimeError("Candidate probe returned malformed evidence")
    return facts


def development_check_facts(source, env):
    if (source / ".git").exists():
        raise RuntimeError("Development checks require an archive without Git metadata")
    checked(["git", "-C", str(source), "init", "--quiet"], env=env, timeout=30)
    checked(["git", "-C", str(source), "add", "--all"], env=env, timeout=60)
    checked(
        [
            "git", "-C", str(source), "-c", "user.name=stack-review", "-c", "user.email=stack-review@localhost",
            "-c", "core.hooksPath=/dev/null", "commit", "--quiet", "--no-gpg-sign", "-m", "Candidate archive",
        ],
        env=env,
        timeout=60,
    )
    check_env = env.copy()
    check_env.pop("LYCEUM_DEV_GNUPG", None)
    check_env["LYCEUM_DEV_REPO"] = str(source)
    checked([str(DEV_RUNNER), "build"], env=check_env, timeout=1800, stage="development image build")
    checks = []
    for name, command in DEV_CHECKS:
        result = run_command([str(DEV_RUNNER), command], env=check_env, timeout=1800)
        if name == "pre-commit":
            checked(["git", "-C", str(source), "reset", "--hard", "--quiet", "HEAD"], env=env, timeout=60)
            checked(["git", "-C", str(source), "clean", "-ffd", "--quiet"], env=env, timeout=60)
        checks.append({"name": name, "status": "passed" if result.returncode == 0 else "failed"})
    return {"checks": checks}


def collect(base, head, home=None, *, dev_tests=False):
    valid_commit(base)
    valid_commit(head)
    root = home or Path(os.environ.get("STACK_REVIEW_HOME", Path.home() / ".stack-review"))
    runs = root / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(HOME=str(Path.home()), GIT_TERMINAL_PROMPT="0", PYTHONDONTWRITEBYTECODE="1")
    lock_path = root / "runtime.lock"
    with lock_path.open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another runtime test is already active") from error
        repository = prepare_repository(root, base, head, env)
        with tempfile.TemporaryDirectory(prefix="candidate-", dir=runs) as temporary:
            directory = Path(temporary)
            source = directory / "candidate"
            archive_commit(repository, head, source, env)
            if not (source / "iris" / "inference_proxy" / "Dockerfile").is_file():
                raise RuntimeError("Candidate has no inference-proxy Dockerfile")
            runtime_env = directory / "runtime.env"
            tokens = {
                "CALLER_TOKEN": secrets.token_urlsafe(40),
                "SERVICE_TOKEN": secrets.token_urlsafe(40),
                "ENDPOINT_SECRET": secrets.token_urlsafe(40),
                "SUPABASE_KEY": secrets.token_urlsafe(40),
                "LINKUP_API_KEY": secrets.token_urlsafe(40),
                "REDIS_PASSWORD": secrets.token_urlsafe(40),
                "DEPLOYMENT_ID": "runtime-fake-dep",
            }
            descriptor = os.open(runtime_env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as environment:
                for name, value in tokens.items():
                    environment.write(f"{name}={value}\n")
            env.update(
                tokens,
                CANDIDATE_HEAD=head,
                CANDIDATE_SOURCE=str(source),
                TRUSTED_ASSETS=str(ASSETS),
                RUNTIME_ENV=str(runtime_env),
            )
            project = f"stack-review-{head[:12]}-{secrets.token_hex(6)}"
            env["RUNTIME_IMAGE"] = f"{project}:candidate"
            compose = Compose(project, env)
            try:
                compose.execute("config", "--quiet", timeout=30)
                compose.execute("build", "--pull", "fixture", "inference-proxy", timeout=1500)
                verify_image(compose, head)
                compose.execute("up", "--detach", "--wait", "--wait-timeout", "90", timeout=150)
                facts = comparison_fact(project, env)
            finally:
                compose.cleanup()
            rules = {"9": facts}
            if dev_tests:
                rules["3"] = development_check_facts(source, env)
            return {
                "base": base,
                "head": head,
                "policy_sha256": policy_digest(),
                "runtime": {"candidate_revision_verified": True, "backend": "fake-openai-compatible"},
                "rules": rules,
            }


def interrupted(_number, _frame):
    raise TimeoutError("Candidate runtime deadline exceeded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=valid_commit)
    parser.add_argument("--head", required=True, type=valid_commit)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dev-tests", action="store_true")
    args = parser.parse_args()
    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        observations = collect(args.base, args.head, dev_tests=args.dev_tests)
    except (
        OSError,
        RuntimeError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
        tarfile.TarError,
    ) as error:
        parser.exit(1, f"stack-review-runtime: candidate runtime test failed: {error}\n")
    finally:
        signal.signal(signal.SIGTERM, previous)
    serialized = json.dumps(observations, separators=(",", ":")) + "\n"
    if args.output:
        args.output.write_text(serialized)
    else:
        print(serialized, end="")


if __name__ == "__main__":
    raise SystemExit(main())
