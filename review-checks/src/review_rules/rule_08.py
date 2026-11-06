"""Rule 8: Regression tests detect the regression. Observations are evaluated, never collected from candidate files."""

from review_rules.common import scenarios

PREFIXES = ("iris/", "croesus/", "app/", "stream_execlet/", "daedalus_go/", "infra/", "shared_models/", "db/")
REQUIRED = ("regression", "control")


def evaluate_one(f):
    if f["baseline_tests"] <= 0 or f["candidate_tests"] <= 0:
        return None
    if f["scenario"] == "control":
        return f["baseline_exit"] == 0 and f["candidate_exit"] == 0
    if f["baseline_failure_kind"] != "assertion":
        return None
    return f["baseline_exit"] != 0 and f["candidate_exit"] == 0 and f["behavior_assertions"] > 0


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
