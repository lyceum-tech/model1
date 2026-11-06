"""Rule 7: Private logs and client errors. Observations are evaluated, never collected from candidate files."""

from review_rules.common import scenarios

PREFIXES = ("iris/", "app/", "stream_execlet/", "daedalus_go/", "infra/")
REQUIRED = ("parse-error", "timeout", "redirect", "upstream-error")


def evaluate_one(f):
    if not f["canaries"] or not all(isinstance(token, str) and token for token in f["canaries"]):
        return None
    outputs = (f["captured_logs"], f["client_error"])
    return not any(token in output for token in f["canaries"] for output in outputs)


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
