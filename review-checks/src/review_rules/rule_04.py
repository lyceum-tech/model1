"""Rule 4: retain documented API operations and qualify supported SDK/routing contracts."""

from repository_checks import mapping

from review_rules.common import scenarios, verdict

PREFIXES = ("iris/", "app/", "shared_models/", "infra/ansible/", "daedalus_go/")
REQUIRED = ("sdk", "public-routing", "response-schema")


def compatible(before, after):
    """Detect definite OpenAPI removals, narrowed enums/types, and new required input fields."""
    for path, operations in before.get("paths", {}).items():
        for method, operation in operations.items():
            if method not in ("get", "post", "put", "patch", "delete", "head", "options", "trace"):
                continue
            current = after.get("paths", {}).get(path, {}).get(method)
            if current is None:
                return False
            old_required = {(p["in"], p["name"]) for p in operation.get("parameters", []) if p.get("required")}
            new_required = {(p["in"], p["name"]) for p in current.get("parameters", []) if p.get("required")}
            if new_required - old_required:
                return False
    old = before.get("components", {}).get("schemas", {})
    new = after.get("components", {}).get("schemas", {})
    for name, schema in old.items():
        current = new.get(name)
        if current is None or schema.get("type") != current.get("type"):
            return False
        if schema.get("enum") and set(schema["enum"]) - set(current.get("enum", [])):
            return False
    return True


def evaluate(facts):
    """Compare captured supported-client responses with independent contract fixtures."""
    return scenarios(
        facts,
        REQUIRED,
        lambda f: f["actual_status"] == f["contract_status"] and set(f["required_fields"]) <= set(f["response_fields"]),
    )


def check(before, after, paths, facts):
    """Schema stability alone cannot prove that the implementation still serves clients."""
    schemas = {p for p in before.paths if "openapi" in p.lower() and p.endswith((".json", ".yaml", ".yml"))}
    for path in sorted(schemas):
        if path not in after.paths or not compatible(mapping(before.read(path)), mapping(after.read(path))):
            return verdict("red", "A documented API operation or schema contract was removed or narrowed")
    return evaluate(facts)
