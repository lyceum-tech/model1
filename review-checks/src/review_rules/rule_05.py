"""Rule 5: Normalization before validation. Observations are evaluated, never collected from candidate files."""

from review_rules.common import scenarios

PREFIXES = ("iris/", "app/", "shared_models/")
REQUIRED = ("absent", "null", "empty", "wrong-type", "zero", "negative", "conflicting-aliases")


def evaluate_one(f):
    if f["forwarded"] and f["accepted"] is not True:
        return False
    if f["accepted"]:
        return f["normalized"] == f["validated"] == f["upstream_value"] and not f["ambiguous_aliases"]
    return f["status"] == 400 and f["forwarded"] is False


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
