"""Inspect immutable candidate data using policy shipped with the trusted runner."""

import ast
import hashlib
import json
import re
import shlex
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from gates import git, snapshot_paths

POLICY_PATH = Path(__file__).parent / "review_rules" / "policy.json"


class Snapshot:
    """Read tracked blobs, never candidate files or executable configuration."""

    def __init__(self, repo: Path, revision: str):
        self.repo = repo
        self.revision = revision
        self.paths = snapshot_paths(repo, revision)

    def read(self, path: str) -> str:
        return git(self.repo, "show", f"{self.revision}:{path}")


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys rather than silently accepting the last value."""


def unique_mapping(loader, node):
    pairs = loader.construct_pairs(node)
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate configuration key")
        result[key] = value
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def mapping(text: str) -> dict:
    value = yaml.load(text, Loader=UniqueLoader)
    if not isinstance(value, dict):
        raise ValueError("Expected a mapping")
    return value


def policy() -> dict:
    return json.loads(POLICY_PATH.read_text())


def valid_setting(value, kind: str) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if kind == "port":
        return str(value).isdigit() and 1 <= int(value) <= 65535
    if not isinstance(value, str) or not value.strip():
        return False
    if kind == "https":
        url = urlsplit(value)
        return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password
    if kind == "sops":
        return value.startswith("ENC[AES256_GCM,") and value.endswith(",type:str]")
    raise ValueError("Unknown configuration type in trusted policy")


def configuration_check(candidate: Snapshot) -> dict:
    """Validate declared requirements in each environment without decrypting secrets."""
    rules = policy()
    findings = []
    for environment, path in rules["environments"].items():
        try:
            settings = mapping(candidate.read(path)) if path in candidate.paths else {}
        except (ValueError, TypeError, yaml.YAMLError):
            findings.append({"rule": "CONFIG-1", "path": path, "kind": "invalid-mapping"})
            continue
        for key, requirement in rules["configuration"].items():
            if environment not in requirement.get("environments", rules["environments"]):
                continue
            try:
                valid = valid_setting(settings.get(key), requirement["type"])
            except ValueError:
                valid = False
            if not valid:
                # Neither values nor parser exception text may enter a report.
                findings.append({"rule": "CONFIG-1", "path": path, "key": key, "kind": "missing-or-invalid"})
    return {
        "id": "environment-configuration",
        "status": "failed" if findings else "passed",
        "reason": "Declared requirements checked in every environment; encrypted values were not decrypted",
        "findings": findings,
    }


def commands(document: dict) -> list[str]:
    """Read command-bearing fields, excluding selectors, comments and prose."""
    result = []
    for key, value in document.items():
        if key in ("run", "entry", "uses") and isinstance(value, str):
            result.append(value)
        elif isinstance(value, dict):
            result.extend(commands(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    result.extend(commands(item))
                elif key in ("run", "entry") and isinstance(item, str):
                    result.append(item)
    return result


def references(candidate: Snapshot) -> set[tuple[str, str]]:
    """Extract repository-root script and local action paths from supported config."""
    result = set()
    for path in sorted(candidate.paths):
        if path.endswith("mise.toml") or path.startswith("mise/includes/") and path.endswith(".toml"):
            document = tomllib.loads(candidate.read(path))
        elif path == ".pre-commit-config.yaml" or (
            path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml"))
        ):
            document = mapping(candidate.read(path))
        else:
            continue
        for command in commands(document):
            # These are literal root paths. Dynamic shell/template expressions are
            # not resolved or executed by this check.
            for target in re.findall(
                r"(?<![\w./-])(?:\$(?:LYC_PATH_REPO_ROOT|\{LYC_PATH_REPO_ROOT\})/|\./)?"
                r"((?:mise/scripts|scripts|\.github/actions)/[\w./-]+)",
                command,
            ):
                result.add((path, target))
    return result


def target_exists(candidate: Snapshot, target: str) -> bool:
    if target.startswith(".github/actions/"):
        return any(f"{target}/{name}" in candidate.paths for name in ("action.yml", "action.yaml"))
    return target in candidate.paths


def generator_paths(source: str) -> dict[str, str]:
    """Inspect literal REPO_ROOT path assignments without importing candidate code."""

    def literal(node):
        if isinstance(node, ast.Name) and node.id == "REPO_ROOT":
            return ""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return "/".join(part for part in (literal(node.left), literal(node.right)) if part)
        raise ValueError("Unsupported generator path")

    result = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            for name in node.targets:
                if isinstance(name, ast.Name) and name.id in ("SOURCE", "CONTROLLER"):
                    result[name.id] = literal(node.value)
    return result


def generated_aliases_check(candidate: Snapshot, contract: dict) -> list[dict]:
    """Verify the known alias output and generator destinations using trusted rendering."""
    source, target, generator = (contract[key] for key in ("source", "target", "generator"))
    findings = []
    for path in (source, target, generator):
        if path not in candidate.paths:
            findings.append({"rule": "REF-2", "path": path, "kind": "missing-generator-input-or-output"})
    if findings:
        return findings
    paths = generator_paths(candidate.read(generator))
    if paths != {"SOURCE": source, "CONTROLLER": target}:
        findings.append({"rule": "REF-2", "path": generator, "kind": "generator-destination-changed"})
    aliases = json.loads(candidate.read(source))["vendor_aliases"]
    expected = {
        "_generated": f"generated from {source}. Do not modify: edit the JSON and run {generator}.",
        "aliases": dict(sorted(aliases.items())),
    }
    if json.loads(candidate.read(target)) != expected:
        findings.append({"rule": "REF-2", "path": target, "kind": "stale-generated-output"})
    return findings


def reference_check(before: Snapshot, candidate: Snapshot) -> dict:
    """Catch new broken references and deletions that break unchanged configuration."""
    findings = []
    try:
        previous = references(before)
        for path, target in sorted(references(candidate)):
            if not target_exists(candidate, target) and (
                (path, target) not in previous or target_exists(before, target)
            ):
                findings.append({"rule": "REF-1", "path": path, "target": target, "kind": "missing-target"})
        for contract in policy().get("generators", []):
            if any(path in before.paths | candidate.paths for path in contract.values()):
                findings.extend(generated_aliases_check(candidate, contract))
    except (ValueError, KeyError, TypeError, SyntaxError, yaml.YAMLError):
        return {
            "id": "configuration-references",
            "status": "incomplete",
            "reason": "Could not parse supported configuration or generator inputs; no candidate code was executed",
        }
    return {
        "id": "configuration-references",
        "status": "failed" if findings else "passed",
        "reason": "Literal script/action references and declared generated outputs checked without candidate execution",
        "findings": findings,
    }


def validation_coverage_check(candidate: Snapshot, observations=None) -> dict:
    """Verify validation wiring and any trusted container check results."""
    findings = []
    try:
        inventory = policy()["validation"]
        for path, tasks in inventory["tasks"].items():
            actual = tomllib.loads(candidate.read(path))["tasks"] if path in candidate.paths else {}
            for name, required in tasks.items():
                task = actual.get(name, {})
                if task.get("run") != required["run"] or not set(required.get("depends", [])).issubset(
                    task.get("depends", [])
                ):
                    findings.append({"rule": "CI-1", "path": path, "kind": "validator-task-removed", "task": name})
        for path, required in inventory["workflow_tasks"].items():
            document = mapping(candidate.read(path)) if path in candidate.paths else {}
            invocations = []
            disabled = (False, "false", "${{ false }}")
            for job in document.get("jobs", {}).values():
                if job.get("if") in disabled:
                    continue
                for step in job.get("steps", []):
                    if step.get("if") not in disabled and isinstance(step.get("run"), str):
                        invocations.extend(shlex.split(line, comments=True) for line in step["run"].splitlines())
            for task in required:
                if not any(invocation[:2] == ["mise", "run"] and task in invocation for invocation in invocations):
                    findings.append({"rule": "CI-1", "path": path, "kind": "ci-task-removed", "task": task})
        # Changes to an implementation require review. Matching task names alone
        # cannot establish that a rewritten script still performs its checks.
        for path in inventory["implementations"]:
            if path not in candidate.paths:
                findings.append({"rule": "CI-1", "path": path, "kind": "validator-implementation-missing"})
            elif hashlib.sha256(candidate.read(path).encode()).hexdigest() != inventory.get(
                "implementation_sha256", {}
            ).get(path):
                findings.append({"rule": "CI-2", "path": path, "kind": "validator-implementation-changed"})
        environments = {
            Path(path).stem
            for path in candidate.paths
            if path.startswith("infra/terraform/envs/") and path.endswith(".env")
        } - {"common", "product-common", "platform-common"}
        missing = set(inventory["environments"]) - environments
        findings.extend(
            {"rule": "CI-1", "path": f"infra/terraform/envs/{name}.env", "kind": "environment-removed"}
            for name in sorted(missing)
        )
    except (ValueError, KeyError, TypeError, yaml.YAMLError):
        return {
            "id": "validation-coverage",
            "status": "incomplete",
            "reason": "Could not inspect validation configuration",
        }
    reason = "Required validation tasks, CI calls, and environments checked; runtime results are separate"
    if observations is not None:
        expected = {"pre-commit", "lint", "test-fast", "integration"}
        checks = observations.get("checks") if isinstance(observations, dict) and set(observations) == {"checks"} else None
        if (
            not isinstance(checks, list)
            or len(checks) != len(expected)
            or any(
                not isinstance(check, dict)
                or set(check) != {"name", "status"}
                or check["name"] not in expected
                or check["status"] not in ("passed", "failed")
                for check in checks
            )
            or {check["name"] for check in checks} != expected
        ):
            return {
                "id": "validation-coverage",
                "status": "incomplete",
                "reason": "Container check observations were malformed",
                "findings": findings,
            }
        for check in checks:
            if check["status"] == "failed":
                findings.append({"rule": "CI-3", "kind": "runtime-check-failed", "check": check["name"]})
        failed = ", ".join(sorted(check["name"] for check in checks if check["status"] == "failed"))
        reason = (
            f"Container checks failed: {failed}" if failed else "All Lyceum container check groups passed on the exact candidate archive"
        )
    return {
        "id": "validation-coverage",
        "status": (
            "failed"
            if any(f["rule"] in ("CI-1", "CI-3") for f in findings)
            else "incomplete"
            if findings
            else "passed"
        ),
        "reason": reason,
        "findings": findings,
    }
