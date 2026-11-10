"""Evaluate advisory checks against a GitHub pull request."""

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from gates import git, resolve
from repository_checks import (
    SECURITY_CHECKS,
    Snapshot,
    configuration_check,
    reference_check,
    security_check,
    validation_coverage_check,
)

SUMMARIES = (
    "Required environment configuration",
    "Executable references and generators",
    "CI validation coverage",
    "Supported API and client compatibility",
    "Normalization before validation",
    "Prices and measurable usage",
    "Private logs and client errors",
    "Regression tests detect the regression",
    "Streaming response parity",
    "Stream progress and terminal events",
    "Routing and failover policy",
    "Customer URL network boundary",
    "Reversible infrastructure transitions",
    "Secret rotation and reconciliation",
    "Historical billing correctness",
    "Scoped CI publishing credentials",
    "Alerts match emitted signals",
    "Workload isolation and model-code trust",
    "Secrets in source and logs",
    "Storage version and session lifetime",
    "CI federation and standing privilege",
    "Network exposure and plaintext transport",
    "Service identity, mesh and endpoint auth",
    "SSH bootstrap and VM handover",
    "Platform hardening and lifecycle declarations",
)
COLORS = {"green": "GREEN", "yellow": "YELLOW", "red": "RED"}
USEFUL = {"green": "yes", "yellow": "not yet", "red": "yes"}


def verdict(color: str, reason: str) -> dict:
    return {"status": color, "reason": reason}


def scoped(paths: list[str], prefixes: tuple[str, ...]) -> bool | None:
    known = ("iris/", "app/", "croesus/", "infra/", "daedalus_go/", "stream_execlet/", "shared_models/", "db/")
    for path in paths:
        if path.startswith(prefixes):
            return True
        if path.endswith(".md") or path.startswith("docs/"):
            continue
        if path.startswith(("mise/", ".github/", ".teamcity/")) or not path.startswith(known):
            return None
    return False


def policy_digest() -> str:
    root = Path(__file__).parent
    files = [
        root / name
        for name in ("dev_runtime.py", "review_report.py", "repository_checks.py", "gates.py", "runtime_agent.py")
    ]
    files.extend(sorted((root / "review_rules").glob("*.py")))
    files.extend(
        sorted(
            path
            for path in (root / "runtime_assets").rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    )
    files.append(root / "review_rules" / "policy.json")
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def assess(repo: Path, base: str, head: str, observations: dict | None = None) -> dict:
    base, head = resolve(repo, base), resolve(repo, head)
    before, after = Snapshot(repo, base), Snapshot(repo, head)
    output = git(repo, "log", "--format=", "--name-only", "--no-renames", "-z", f"{base}..{head}")
    paths = sorted({path.strip("\n") for path in output.split("\0") if path.strip("\n")})
    digest = policy_digest()
    evidence = {}
    if observations and all(
        observations.get(key) == value for key, value in (("base", base), ("head", head), ("policy_sha256", digest))
    ):
        evidence = observations.get("rules", {})
    rows = []
    for number, summary in enumerate(SUMMARIES, 1):
        result = verdict("yellow", "Rule adapter not installed in this policy")
        try:
            if number <= 3:
                check = (
                    lambda: configuration_check(after),
                    lambda: reference_check(before, after),
                    lambda: validation_coverage_check(after, evidence.get("3")),
                )[number - 1]()
                result = verdict({"passed": "green", "failed": "red"}.get(check["status"], "yellow"), check["reason"])
                result["findings"] = check.get("findings", [])
            elif number > 17:
                check = security_check(before, after, SECURITY_CHECKS[number - 18])
                result = verdict({"passed": "green", "failed": "red"}.get(check["status"], "yellow"), check["reason"])
                result["findings"] = check.get("findings", [])
            else:
                name = f"review_rules.rule_{number:02}"
                if importlib.util.find_spec(name) is not None:
                    module = importlib.import_module(name)
                    applies = scoped(paths, module.PREFIXES)
                    if applies is False:
                        result = verdict("green", "No changes in this rule's declared scope")
                    elif applies is None:
                        result = verdict("yellow", "Shared or unfamiliar paths need explicit qualification")
                    else:
                        result = module.check(before, after, paths, evidence.get(str(number)))
        except Exception:
            result = verdict("yellow", "Rule inspection failed or observations are malformed")
        if result.get("status") not in COLORS:
            result = verdict("yellow", "Invalid rule result")
        useful = USEFUL[result["status"]]
        rows.append({"number": number, "summary": summary, **result, "useful": useful})
    return {"base": base, "head": head, "policy_sha256": digest, "advisory": True, "rules": rows}


def _cells(row: dict) -> list[str]:
    reason = " ".join(str(row.get("reason", "No result available")).split())
    suffix = f"; {len(findings)} finding(s), use --json for details" if (findings := row.get("findings")) else ""
    if len(reason) + len(suffix) > 79:
        reason = reason[: 76 - len(suffix)] + "..."
    reason += suffix
    return [
        str(row.get("number", "")),
        row.get("summary", "Unknown check"),
        COLORS.get(row.get("status"), "YELLOW"),
        USEFUL.get(row.get("status"), "not yet"),
        reason,
    ]


def render(report: dict) -> str:
    by_number = {row["number"]: row for row in report.get("rules", [])}
    rows = [
        _cells(by_number.get(number, {"number": number, "summary": summary}))
        for number, summary in enumerate(SUMMARIES, 1)
    ]
    header = ["#", "Check", "Status", "Useful", "Why"]
    widths = [max(len(row[index]) for row in [header, *rows]) for index in range(len(header))]

    def line(row: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(row)) + " |"

    separator = "|-" + "-|-".join("-" * width for width in widths) + "-|"
    return "\n".join([line(header), separator, *(line(row) for row in rows)])


def summary(report: dict) -> str:
    counts = {color: 0 for color in COLORS}
    for row in report["rules"]:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    useful = sum(counts[color] for color in ("green", "red"))
    return (
        f"{len(report['rules'])} checks: {counts['green']} green, {counts['red']} red, "
        f"{counts['yellow']} yellow; {useful} informative, {len(report['rules']) - useful} not yet useful"
    )


def gh(*args: str):
    command = ["gh", "api", *args]
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)
    if result.returncode:
        raise ValueError("GitHub API request failed; check gh authentication and the pull request URL")
    return json.loads(result.stdout)


def parse_target(target: str, default_repository: str) -> tuple[str, int]:
    if target.isdigit():
        return default_repository, int(target)
    url = urlsplit(target)
    if url.scheme != "https" or url.netloc != "github.com":
        raise ValueError("Use a full GitHub pull request URL or a PR number")
    match = re.fullmatch(r"/([\w.-]+)/([\w.-]+)/pull/(\d+)/?", url.path)
    if not match:
        raise ValueError("Use a full GitHub pull request URL or a PR number")
    return f"{match[1]}/{match[2]}", int(match[3])


def fetch(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), "fetch", "--filter=blob:none", "origin", *args],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if result.returncode:
        raise ValueError("Could not fetch the pull request commits; check repository access and --repo")


def prepare_cache(repository: str, number: int, pr: dict, cache_root: Path) -> Path:
    destination = cache_root / f"{repository.replace('/', '--')}.git"
    if destination.exists():
        subprocess.run(
            ["git", "-C", str(destination), "remote", "set-url", "origin", f"https://github.com/{repository}.git"],
            capture_output=True,
            check=True,
            timeout=30,
        )
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "init", "--bare", "--quiet", str(destination)], capture_output=True, check=True, timeout=30
        )
        subprocess.run(
            ["git", "-C", str(destination), "remote", "add", "origin", f"https://github.com/{repository}.git"],
            capture_output=True,
            check=True,
            timeout=30,
        )
    fetch(
        destination,
        f"+refs/heads/{pr['base']['ref']}:refs/remotes/origin/{pr['base']['ref']}",
        f"+refs/pull/{number}/head:refs/remotes/pull/{number}/head",
    )
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", help="GitHub PR URL, or PR number in --repository")
    parser.add_argument("--repository", default="lyceum-tech/lyceum", help="Repository used with a numeric PR")
    parser.add_argument("--repo", type=Path, help="Existing target-repository clone; otherwise use an isolated cache")
    parser.add_argument("--observations", type=Path, help="Trusted candidate/policy-bound observation JSON")
    parser.add_argument("--json", action="store_true", help="Print the complete report as JSON")
    parser.add_argument("--cache-dir", type=Path, help="Repository cache directory")
    parser.add_argument("--dev-vm", metavar="USER@HOST", help="Build and probe this PR on a Linux Docker host")
    parser.add_argument(
        "--dev-tests", action="store_true", help="Also run Lyceum's full check groups in its Docker development environment"
    )
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repository):
            raise ValueError("Invalid repository")
        repository, number = parse_target(args.target, args.repository)
        if args.dev_tests and not args.dev_vm:
            raise ValueError("--dev-tests requires --dev-vm")
        if args.dev_vm and (repository != "lyceum-tech/lyceum" or args.observations):
            raise ValueError("--dev-vm supports the Lyceum PR and remote observations only")
        pr = gh(f"repos/{repository}/pulls/{number}")
        if pr["state"] != "open":
            raise ValueError("The pull request is not open")
        base, head = pr["base"]["sha"], pr["head"]["sha"]
        if not all(re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (base, head)):
            raise ValueError("GitHub returned an invalid commit")
        if args.repo:
            repo = args.repo.resolve()
            fetch(repo, base, head)
        else:
            cache = args.cache_dir or (Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "stack-review")
            repo = prepare_cache(repository, number, pr, cache)
        if args.dev_vm:
            from dev_runtime import collect

            observations = collect(args.dev_vm, base, head, policy_digest(), tests=args.dev_tests)
        else:
            observations = json.loads(args.observations.read_text()) if args.observations else None
        report = assess(repo, base, head, observations)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"stack-review: {error}\n")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{pr['html_url']}\n{pr['title']}\n")
        print(render(report))
        print(f"\n{summary(report)}")
        print(f"Base: {report['base']}  Head: {report['head']}  Policy: {report['policy_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
