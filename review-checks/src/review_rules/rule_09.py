"""Rule 9: Streaming response parity. Observations are evaluated, never collected from candidate files."""

from review_rules.common import scenarios

PREFIXES = ("iris/", "app/", "shared_models/")
REQUIRED = ("plain", "tools", "search", "stop-string")


def evaluate_one(f):
    fields = ("text", "model", "usage", "finish_reason")
    return all(f["assembled_stream"][key] == f["complete_response"][key] for key in fields)


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
