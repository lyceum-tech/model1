"""Rule 17: Alerts match emitted signals. Observations are evaluated, never collected from candidate files."""

import re

from review_rules.common import scenarios

PREFIXES = ("infra/terraform/grafana/", "iris/", "croesus/", "daedalus_go/", "stream_execlet/")
REQUIRED = ("positive", "negative", "resolution")


def evaluate_one(f):
    if f["scenario"] == "resolution":
        return f["resolved"] is True
    matches = [
        event
        for event in f["emitted_events"]
        if re.search(f["message_regex"], event["message"]) and event["severity"] in f["accepted_severities"]
    ]
    if bool(matches) != f["expected_match"]:
        return False
    return all(set(event["labels"]) <= set(f["bounded_labels"]) for event in matches)


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
