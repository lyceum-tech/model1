"""Read immutable Git snapshots without executing candidate code."""

import subprocess
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise ValueError("Git could not resolve or inspect the requested revisions")
    return result.stdout


def resolve(repo: Path, revision: str) -> str:
    return git(repo, "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}").strip()


def snapshot_paths(repo: Path, revision: str) -> set[str]:
    return set(filter(None, git(repo, "ls-tree", "-r", "--name-only", "-z", revision).split("\0")))
