"""Rule 11: Routing and failover policy. Observations are evaluated, never collected from candidate files."""

from review_rules.common import scenarios

PREFIXES = ("iris/", "app/", "shared_models/", "llm-router/")
REQUIRED = ("cold-start", "partial-outage", "restricted-org", "pre-write-failure", "post-write-failure")


def evaluate_one(f):
    for index, attempt in enumerate(f["attempts"]):
        if attempt["destination"] not in f["permitted_destinations"]:
            return False
        if index > 0 and attempt["after_first_output"]:
            return False
    if not f["model_known"]:
        return f["status"] == (404 if f["catalogues_complete"] else 503)
    return f["status"] in (200, 503, 502, 504)


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
