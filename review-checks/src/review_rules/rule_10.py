"""Rule 10: Stream progress and terminal events. Observations are evaluated, never collected from candidate files."""

from review_rules.common import scenarios

PREFIXES = ("iris/", "app/", "stream_execlet/", "daedalus_go/")
REQUIRED = ("string-argument", "array-argument", "object-argument", "cancellation", "invalid-message", "queue-pressure")


def evaluate_one(f):
    if not f["events"] or f["idle_limit_ms"] <= 0:
        return None
    ended = set()
    turns = set()
    previous = 0
    for event in f["events"]:
        turn, kind, timestamp = event["turn"], event["kind"], event["time_ms"]
        if timestamp < previous or timestamp - previous >= f["idle_limit_ms"]:
            return False
        previous = timestamp
        turns.add(turn)
        if turn in ended or kind not in ("content", "heartbeat", "done", "error", "closed"):
            return False
        if kind in ("done", "error", "closed"):
            ended.add(turn)
    return ended == turns


def evaluate(facts):
    """Classify complete candidate-bound observations, with missing evidence yellow."""
    return scenarios(facts, REQUIRED, evaluate_one)


def check(before, after, paths, facts):
    """The reporter supplies only trusted, commit-bound observations for relevant changes."""
    return evaluate(facts)
