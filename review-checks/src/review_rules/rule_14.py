"""Rule 14: Secret rotation and reconciliation. Observations are evaluated, never collected from candidate files."""

from review_rules.common import scenarios

PREFIXES = ("infra/", "iris/", "app/", "daedalus_go/")
REQUIRED = ("prepend-new-key", "rollout", "reconcile", "retire-old-key")


def evaluate_one(f):
    active = set(f["active_key_ids"])
    return (
        f["issued_key_id"] == f["expected_issuing_key_id"]
        and f["issued_key_id"] in active
        and set(f["required_blob_ids"]) <= set(f["readable_blob_ids"])
        and not (active & set(f["disabled_key_ids"]))
        and set(f["after_reconcile_key_ids"]) == active
    )


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
