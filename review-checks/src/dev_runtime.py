"""Collect commit-bound observations from an explicitly selected Linux Docker host."""

import json
import os
import re
import shlex
import subprocess

MAX_OBSERVATION_BYTES = 256 * 1024
COMMIT = re.compile(r"[0-9a-f]{40}")
HOST = re.compile(r"[A-Za-z][A-Za-z0-9-]{0,62}(?:\.[A-Za-z][A-Za-z0-9-]{0,62})*")
USER = re.compile(r"[a-z_][a-z0-9_-]*\$?")


def validate_host(value):
    if not isinstance(value, str) or "@" not in value:
        raise ValueError("Use --dev-vm USER@HOST for a Linux account")
    user, hostname = value.rsplit("@", 1)
    if user == "root" or not USER.fullmatch(user) or not HOST.fullmatch(hostname):
        raise ValueError("Use a non-root Linux account and a DNS hostname for --dev-vm")
    return value


def validate_observations(data, base, head, policy):
    if not isinstance(data, dict) or set(data) != {"base", "head", "policy_sha256", "runtime", "rules"}:
        raise ValueError("Remote runtime returned malformed observations")
    if not COMMIT.fullmatch(base) or not COMMIT.fullmatch(head) or not re.fullmatch(r"[0-9a-f]{64}", policy):
        raise ValueError("Invalid expected candidate binding")
    if data["base"] != base or data["head"] != head or data["policy_sha256"] != policy:
        raise ValueError("Remote runtime is not bound to the requested candidates and policy")
    if data["runtime"] != {"candidate_revision_verified": True, "backend": "fake-openai-compatible"}:
        raise ValueError("Remote runtime did not verify its candidate image")
    if not isinstance(data["rules"], dict):
        raise ValueError("Remote runtime returned malformed rules")
    encoded = json.dumps(data, separators=(",", ":")).encode()
    if len(encoded) > MAX_OBSERVATION_BYTES:
        raise ValueError("Remote runtime observations exceed their size limit")
    return data


def collect(host, base, head, policy, timeout=2100):
    validate_host(host)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 60 <= timeout <= 3600:
        raise ValueError("Runtime timeout is outside its permitted range")
    command = (
        f"exec timeout --signal=TERM --kill-after=30s {timeout}s stack-review-runtime "
        f"--base {shlex.quote(base)} --head {shlex.quote(head)}"
    )
    environment = os.environ.copy()
    environment["LC_ALL"] = "C.UTF-8"
    result = subprocess.run(
        [
            "ssh",
            "-T",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=15",
            "-o",
            "ServerAliveInterval=15",
            "-o",
            "ServerAliveCountMax=4",
            "--",
            validate_host(host),
            command,
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
        timeout=timeout + 45,
        env=environment,
    )
    if result.returncode != 0:
        raise ValueError("Remote candidate test failed; check SSH, gh, Docker, installation, and cleanup logs")
    if len(result.stdout.encode()) > MAX_OBSERVATION_BYTES:
        raise ValueError("Remote runtime observations exceed their size limit")
    return validate_observations(json.loads(result.stdout), base, head, policy)
