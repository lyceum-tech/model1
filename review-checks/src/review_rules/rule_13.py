"""Rule 13: Reversible infrastructure transitions. Observations are evaluated, never collected from candidate files."""

from review_rules.common import scenarios

PREFIXES = ("infra/", "stream_execlet/", "iris/")
REQUIRED = ("forward-transition", "reverse-transition", "restart")


def evaluate_one(f):
    if set(f["actual_active_services"]) != set(f["desired_active_services"]):
        return False
    if any(len(owners) != 1 for owners in f["resource_owners"].values()):
        return False
    return f["workload_succeeded"] is True and not (set(f["obsolete_services"]) & set(f["enabled_services"]))


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
